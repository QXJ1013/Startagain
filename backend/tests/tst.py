# tests/test_router_bugcheck_plus.py
import os, sys, json, argparse, re, difflib
from typing import Any, Dict, List, Tuple

# make app importable
sys.path.append(os.path.abspath("."))

from app.config import get_settings
from app.deps import get_lexicon_router
from app.vendors.ibm_cloud import RAGQueryClient

try:
    import ahocorasick
    HAVE_AC = True
except Exception:
    HAVE_AC = False


def to_lower_ascii(s: str) -> str:
    s = (s or "").lower()
    try:
        s = s.encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass
    return s

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_terms_block(body: Any) -> Dict[str, List[str]]:
    # A: {"terms": {...}}, B: flat dict, C: [{"term","aliases"}], D: ["Term",...]
    if not body:
        return {}
    if isinstance(body, dict) and isinstance(body.get("terms"), dict):
        return {str(k): list(v or []) for k, v in body["terms"].items()}
    if isinstance(body, dict) and all(isinstance(v, (list, tuple)) for v in body.values()):
        return {str(k): list(v or []) for k, v in body.items()}
    if isinstance(body, list) and body and isinstance(body[0], dict):
        out = {}
        for row in body:
            t = str(row.get("term") or "").strip()
            if t:
                out[t] = list(row.get("aliases") or [])
        return out
    if isinstance(body, list):
        return {str(t): [] for t in body}
    return {}

def build_ac(lex: Dict[str, Any]):
    A = ahocorasick.Automaton()
    total_entries = 0
    pnm_term_counts = {}
    for pnm, body in (lex or {}).items():
        tmap = parse_terms_block(body)
        pnm_term_counts[pnm] = len(tmap)
        for term, aliases in tmap.items():
            for w in [term] + list(aliases or []):
                key = to_lower_ascii(w)
                if key:
                    A.add_word(key, (term, pnm, w))
                    total_entries += 1
    A.make_automaton()
    return A, total_entries, pnm_term_counts

def ac_scan(A, text: str) -> List[Tuple[int, str, str, str]]:
    res = []
    txt = to_lower_ascii(text or "")
    for end, payload in A.iter(txt):
        term, pnm, alias = payload
        start = end - len(to_lower_ascii(alias)) + 1
        res.append((start, alias, term, pnm))
    res.sort(key=lambda x: x[0])
    return res

def approx_hints(text: str, lex: Dict[str, Any], topn: int = 8) -> List[Tuple[str, str, float]]:
    tokens = re.findall(r"[a-zA-Z]+", to_lower_ascii(text))
    all_aliases = []
    for _, body in (lex or {}).items():
        tmap = parse_terms_block(body)
        for term, aliases in tmap.items():
            all_aliases.append(to_lower_ascii(term))
            for a in aliases or []:
                all_aliases.append(to_lower_ascii(a))
    uniq_aliases = sorted(set([a for a in all_aliases if a]))
    hints = []
    for tok in tokens:
        sims = sorted(
            [(cand, difflib.SequenceMatcher(None, tok, cand).ratio()) for cand in uniq_aliases],
            key=lambda x: x[1], reverse=True
        )[:topn]
        if sims:
            cand, score = sims[0]
            hints.append((tok, cand, score))
    hints = sorted(hints, key=lambda x: x[2], reverse=True)[:topn]
    return hints

def print_section(title: str):
    print("\n" + "="*10 + f" {title} " + "="*10)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", type=str, default="My hands feel weak and I sometimes struggle to breathe at night.")
    args = parser.parse_args()

    s = get_settings()
    print_section("CONFIG")
    print("PNM_LEXICON_PATH:", getattr(s, "PNM_LEXICON_PATH", None))
    print("ENABLE_SEMANTIC_BACKOFF:", getattr(s, "ENABLE_SEMANTIC_BACKOFF", None))
    print("BACKGROUND_VECTOR_INDEX_ID:", getattr(s, "BACKGROUND_VECTOR_INDEX_ID", None))
    print("QUESTION_VECTOR_INDEX_ID:", getattr(s, "QUESTION_VECTOR_INDEX_ID", None))

    # Load lexicon
    print_section("LEXICON")
    lex = load_json(getattr(s, "PNM_LEXICON_PATH"))
    pnms = list(lex.keys())
    terms_total = sum(len(parse_terms_block(lex[p])) for p in pnms)
    print("PNMs:", len(pnms))
    print("Terms:", terms_total)
    for p in pnms[:3]:
        tmap = parse_terms_block(lex[p])
        print(f"- {p}: {list(tmap.keys())[:3]}")

    # AC
    print_section("AC AUTOMATON")
    if not HAVE_AC:
        print("!! python-ahocorasick missing")
        A = None
    else:
        A, total, counts = build_ac(lex)
        print("Total entries loaded into AC:", total)
        hits = ac_scan(A, args.q)
        if hits:
            print(f"AC hits for {args.q!r}:")
            for start, alias, term, pnm in hits:
                print(f"  pos={start:>3} alias={alias!r} -> term={term!r}, pnm={pnm!r}")
        else:
            print("No AC hits.")
            hints = approx_hints(args.q, lex)
            if hints:
                print("Approx hints (token ~ closest alias, sim):")
                for tok, cand, sc in hints:
                    print(f"  {tok:>12} ~ {cand:<20} ({sc:.2f})")

    # RAG raw
    rag = RAGQueryClient()
    print_section("RAGQUERY RAW (BACKGROUND)")
    try:
        docs_bg = rag.search(args.q, top_k=5, index_kind="background")
        if not docs_bg:
            print("(no vector docs)")
        else:
            print(f"got {len(docs_bg)} docs; first doc keys:", list(docs_bg[0].keys()))
            md = docs_bg[0].get("metadata") or {}
            print("metadata keys:", list(md.keys()))
            print("md.pnm:", md.get("pnm"), "md.term:", md.get("term"))
            print("text.head:", (docs_bg[0].get("text") or "")[:120].replace("\n"," "))
    except Exception as e:
        print("!! RAGQuery background failed:", repr(e))

    print_section("RAGQUERY RAW (QUESTION)")
    try:
        docs_q = rag.search(args.q, top_k=5, index_kind="question")
        if not docs_q:
            print("(no vector docs)")
        else:
            print(f"got {len(docs_q)} docs; first doc keys:", list(docs_q[0].keys()))
            md = docs_q[0].get("metadata") or {}
            print("metadata keys:", list(md.keys()))
            print("md.pnm:", md.get("pnm"), "md.term:", md.get("term"))
            print("text.head:", (docs_q[0].get("text") or "")[:120].replace("\n"," "))
    except Exception as e:
        print("!! RAGQuery question failed:", repr(e))

    # Router step-by-step (without fallback)
    print_section("LEXICON_ROUTER.locate()")
    router = get_lexicon_router()
    try:
        # monkey-patch: wrap internal semantic call to show inputs/outputs if available
        rag_cli = getattr(router, "rag", None)
        bm25_cli = getattr(router, "bm25", None)
        print("Router has RAG channel:", bool(rag_cli), "BM25 channel:", bool(bm25_cli))
        hits = router.locate(args.q)
        print("router.locate hits:", hits)
    except Exception as e:
        print("!! router.locate failed:", repr(e))

    # Exit code: fail if both AC and router hits are empty
    ac_ok = False
    if HAVE_AC and 'A' in locals() and A:
        ac_ok = bool(ac_scan(A, args.q))
    if not ac_ok and not hits:
        print("\nFAIL: AC and Router both empty -> check lexicon alias coverage and RAG index content.")
        sys.exit(2)
    print("\nOK: at least one of AC/Router produced hits.")
    sys.exit(0)

if __name__ == "__main__":
    main()
