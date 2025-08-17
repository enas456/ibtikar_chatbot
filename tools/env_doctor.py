# save as tools/env_doctor.py and run: python tools/env_doctor.py
import os, json
from dotenv import load_dotenv; load_dotenv()
keys = ["FAISS_INDEX_PATH","DOCS_JSON_PATH","METADATA_PATH","BGE_MODEL_PATH","HF_HOME"]
for k in keys:
    v = os.getenv(k)
    print(f"{k} = {v}   {'[OK]' if v and (os.path.exists(v) or k in ['BGE_MODEL_PATH','HF_HOME']) else ''}")
