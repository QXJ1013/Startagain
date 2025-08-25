# tests/vendor_map_probe.py
import os, sys, argparse, getpass
sys.path.append(os.path.abspath("."))

from ibm_watsonx_ai import APIClient
from ibm_watsonx_ai.foundation_models.utils import Toolkit
from app.vendors.ibm_cloud import RAGQueryClient

def main():
    apikey = os.getenv("WATSONX_APIKEY") or os.getenv("IBM_CLOUD_API_KEY")
    if not apikey:
        apikey = getpass.getpass("IBM Cloud API key: ")
    url = os.getenv("WATSONX_URL", "https://eu-gb.ml.cloud.ibm.com")
    space_id = os.getenv("SPACE_ID") or os.getenv("WATSONX_SPACE_ID")
    project_id = os.getenv("PROJECT_ID") or os.getenv("WATSONX_PROJECT_ID")
    bg = os.getenv("BACKGROUND_VECTOR_INDEX_ID")
    qx = os.getenv("QUESTION_VECTOR_INDEX_ID")

    p = argparse.ArgumentParser()
    p.add_argument("--q", default="breathing at night and weak hands")
    args = p.parse_args()

    print("=== INPUT ===")
    print("space_id:", space_id, "project_id:", project_id)
    print("bg:", bg, "q:", qx)

    # Toolkit baseline (project only vs space only)
    api_client = APIClient({"url": url, "apikey": apikey})
    tool = Toolkit(api_client=api_client).get_tool("RAGQuery")

    for label, vid in [("BG", bg), ("Q", qx)]:
        if not vid: 
            print(label, "missing id"); 
            continue
        for mode, cfg in [
            ("space",   {"vectorIndexId": vid, "spaceId": space_id}),
            ("project", {"vectorIndexId": vid, "projectId": project_id}),
        ]:
            try:
                r = tool.run(input=args.q, config=cfg)
                print(f"[TK/{label}/{mode}] docs={len(r.get('documents') or [])} out_len={len(r.get('output') or '')}")
            except Exception as e:
                print(f"[TK/{label}/{mode}] ERROR -> {e}")

    # Vendor path
    rag = RAGQueryClient()
    for kind in ("background", "question"):
        try:
            docs = rag.search(args.q, top_k=5, index_kind=kind)
            print(f"[VENDOR/{kind}] docs={len(docs)}")
        except Exception as e:
            print(f"[VENDOR/{kind}] ERROR -> {e}")

if __name__ == "__main__":
    main()
