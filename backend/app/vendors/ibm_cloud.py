# app/vendors/ibm_cloud.py
# Minimal IBM Cloud wrappers for RAGQuery / LLM.
# Key points:
# - Set default project/space on APIClient.
# - Pass BOTH projectId and spaceId in RAGQuery config (SDK picks the valid one).
# - Lazy import to avoid import-time errors.
from __future__ import annotations
from typing import Any, Dict, List, Optional
from app.config import get_settings
import os
import sys

# Set UTF-8 encoding for Windows compatibility
if sys.platform.startswith('win'):
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # Try to set console codepage to UTF-8
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except:
        pass


class RAGQueryClient:
    def __init__(self, settings=None) -> None:
        self.cfg = settings or get_settings()

    # -------- helpers --------
    def _vector_id(self, kind: str) -> Optional[str]:
        k = (kind or "background").lower()
        if k == "background":
            return getattr(self.cfg, "BACKGROUND_VECTOR_INDEX_ID", None)
        if k == "question":
            return getattr(self.cfg, "QUESTION_VECTOR_INDEX_ID", None)
        return getattr(self.cfg, "VECTOR_INDEX_ID", None)

    def _api_client(self):
        from ibm_watsonx_ai import APIClient  # lazy
        url = getattr(self.cfg, "WATSONX_URL", None)
        key = getattr(self.cfg, "WATSONX_APIKEY", None)
        if not url or not key:
            raise RuntimeError("WATSONX_URL/WATSONX_APIKEY missing.")
        api = APIClient({"url": url, "apikey": key})

        # Set default scope on client (important for some toolkit paths)
        proj = getattr(self.cfg, "PROJECT_ID", None)
        space = getattr(self.cfg, "SPACE_ID", None)
        try:
            if proj and hasattr(api.set, "default_project"):
                api.set.default_project(proj)  # newer SDKs
        except Exception:
            pass
        try:
            if space and hasattr(api.set, "default_space"):
                api.set.default_space(space)
        except Exception:
            pass
        return api

    # -------- public --------
    def healthy(self) -> bool:
        try:
            has_url = bool(getattr(self.cfg, "WATSONX_URL", None))
            has_key = bool(getattr(self.cfg, "WATSONX_APIKEY", None))
            has_scope = bool(getattr(self.cfg, "PROJECT_ID", None) or getattr(self.cfg, "SPACE_ID", None))
            has_idx = bool(self._vector_id("background") or self._vector_id("question"))
            return has_url and has_key and has_scope and has_idx
        except Exception:
            return False

    def search(self, query: str, top_k: int = 5, index_kind: str = "background") -> List[Dict[str, Any]]:
        """
        Return normalized docs: [{"text":..., "metadata":..., "score":...}, ...]
        """
        vec_id = self._vector_id(index_kind)
        if not vec_id:
            return []

        api = self._api_client()
        from ibm_watsonx_ai.foundation_models.utils import Toolkit  # lazy
        tool = Toolkit(api_client=api).get_tool("RAGQuery")

        # Use either projectId OR spaceId, not both
        # Try project first, fallback to space if vector index not found
        cfg: Dict[str, Any] = {
            "vectorIndexId": vec_id,
            "top_k": top_k,
        }
        proj = getattr(self.cfg, "PROJECT_ID", None)
        space = getattr(self.cfg, "SPACE_ID", None)
        
        res = None
        last_error = None
        
        # Helper function to run query with encoding error handling
        def safe_run_query(config):
            try:
                return tool.run(input=query, config=config) or {}
            except UnicodeEncodeError:
                # Handle Windows encoding issues by trying different approaches
                try:
                    import locale
                    original_locale = locale.getlocale()
                    try:
                        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                    except:
                        try:
                            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                        except:
                            pass
                    
                    result = tool.run(input=query, config=config) or {}
                    locale.setlocale(locale.LC_ALL, original_locale)
                    return result
                except:
                    # If all else fails, try with a simpler query
                    try:
                        simple_query = query.encode('ascii', errors='ignore').decode('ascii')
                        return tool.run(input=simple_query, config=config) or {}
                    except:
                        return {"documents": [], "output": "Encoding error prevented query execution"}
            except Exception as e:
                raise e
        
        # Try space first (vector indexes are associated with spaces, not projects)
        if space:
            try:
                cfg = {"vectorIndexId": vec_id, "spaceId": space, "top_k": top_k}
                res = safe_run_query(cfg)
                print(f"[IBM_SUCCESS] Space query successful for index {vec_id[:8]}...")
            except Exception as e:
                print(f"[IBM_SPACE_ERROR] Space query failed: {e}")
                last_error = e
                res = None

        # Try project as fallback (though vector indexes are typically space-based)
        if res is None and proj:
            try:
                cfg = {"vectorIndexId": vec_id, "projectId": proj, "top_k": top_k}
                res = safe_run_query(cfg)
                print(f"[IBM_FALLBACK] Project query successful for index {vec_id[:8]}...")
            except Exception as e:
                print(f"[IBM_PROJECT_ERROR] Project query failed: {e}")
                last_error = e
                res = None
        
        # If still no response, return empty results or raise the last error
        if res is None:
            if last_error:
                # Handle encoding errors gracefully
                if "codec can't encode" in str(last_error):
                    return []  # Return empty results for encoding issues
                raise last_error
            return []
        
        # Handle both structured documents and text output formats    
        docs = res.get("documents") or []
        out: List[Dict[str, Any]] = []
        
        # If we have structured documents, use them
        if docs:
            for d in docs:
                # Safely handle text content with potential encoding issues
                text = d.get("text") or d.get("content") or ""
                if isinstance(text, str):
                    # Replace problematic unicode characters
                    text = text.encode('utf-8', errors='ignore').decode('utf-8')
                    
                out.append({
                    "text": text,
                    "metadata": d.get("metadata") or {},
                    "score": d.get("score") or d.get("similarity") or None,
                })
        
        # If no structured documents but we have output text, parse it
        elif res.get("output"):
            output_text = res["output"]
            if isinstance(output_text, str) and len(output_text.strip()) > 0:
                # Check for error messages in output
                error_indicators = [
                    "Error: Failure querying documents",
                    "Failed to retrieve",
                    "does_not_exist",
                    "Unexpected resp",
                    "error:",
                    "Error:",
                    "failed"
                ]

                output_lower = output_text.lower()
                if any(indicator.lower() in output_lower for indicator in error_indicators):
                    # This is an error message, not valid content
                    print(f"[RAG_ERROR] Watson API returned error: {output_text[:100]}...")
                    return []

                # Clean the output text
                cleaned_text = output_text.encode('utf-8', errors='ignore').decode('utf-8')

                # Try to split the output into chunks if it contains multiple results
                # This is a heuristic approach since we don't know the exact format
                chunks = []
                if len(cleaned_text) > 500:
                    # Split by common separators that might indicate document boundaries
                    potential_splits = cleaned_text.split('\n\n')
                    if len(potential_splits) > 1:
                        chunks = [chunk.strip() for chunk in potential_splits if len(chunk.strip()) > 50]

                if not chunks:
                    chunks = [cleaned_text.strip()]

                # Create documents from chunks
                for i, chunk in enumerate(chunks[:top_k]):  # Respect top_k limit
                    out.append({
                        "text": chunk,
                        "metadata": {"chunk_index": i, "source": "output_text"},
                        "score": None,  # No score available for output text
                    })
        
        return out


class LLMClient:
    def __init__(
        self,
        model_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        settings=None
    ) -> None:
        self.cfg = settings or get_settings()
        self.model_id = model_id or getattr(self.cfg, "AI_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")
        self.params = params or {"max_new_tokens": 512, "temperature": 0.2}

    def _mi(self):
        from ibm_watsonx_ai import APIClient
        from ibm_watsonx_ai.foundation_models import ModelInference
        url = getattr(self.cfg, "WATSONX_URL", None)
        key = getattr(self.cfg, "WATSONX_APIKEY", None)
        if not url or not key:
            raise RuntimeError("WATSONX_URL/WATSONX_APIKEY missing.")
        api = APIClient({"url": url, "apikey": key})

        proj = getattr(self.cfg, "PROJECT_ID", None)
        space = getattr(self.cfg, "SPACE_ID", None)

        # Set defaults on client (best-effort)
        try:
            if proj and hasattr(api.set, "default_project"):
                api.set.default_project(proj)
        except Exception:
            pass
        try:
            if space and hasattr(api.set, "default_space"):
                api.set.default_space(space)
        except Exception:
            pass

        kwargs: Dict[str, Any] = dict(model_id=self.model_id, api_client=api, params=self.params)
        if proj:
            kwargs["project_id"] = proj
        elif space:
            kwargs["space_id"] = space
        else:
            raise RuntimeError("Neither PROJECT_ID nor SPACE_ID provided.")
        return ModelInference(**kwargs)

    def healthy(self) -> bool:
        return bool(
            getattr(self.cfg, "WATSONX_URL", None)
            and getattr(self.cfg, "WATSONX_APIKEY", None)
            and (getattr(self.cfg, "PROJECT_ID", None) or getattr(self.cfg, "SPACE_ID", None))
        )

    def generate_text(self, prompt: str) -> str:
        """Generate text response from the LLM"""
        mi = self._mi()
        out = mi.generate(prompt=prompt)
        if isinstance(out, dict):
            try:
                return (out["results"][0]["generated_text"] or "").strip()
            except Exception:
                return ""
        elif isinstance(out, str):
            return out.strip()
        return ""

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        import re, json
        text = self.generate_text(prompt)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
