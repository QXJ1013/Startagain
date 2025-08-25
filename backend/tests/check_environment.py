import os, sys, argparse, getpass
sys.path.append(os.path.abspath("."))
from app.config import get_settings

s = get_settings()
print("WATSONX_URL:", s.WATSONX_URL)
print("WATSONX_APIKEY set:", bool(s.WATSONX_APIKEY))
print("SPACE_ID:", s.SPACE_ID)
print("PROJECT_ID:", s.PROJECT_ID)
print("BACKGROUND_VECTOR_INDEX_ID:", s.BACKGROUND_VECTOR_INDEX_ID)
print("QUESTION_VECTOR_INDEX_ID:", s.QUESTION_VECTOR_INDEX_ID)
