# Ibtikar Chatbot

A retrieval-augmented chatbot that answers using:
- **Google Docs** (exported as text via Drive API)
- **Teknofest site** content
- **Ibtikar site** content (`https://ibtikar.org.tr/ar/`)
- **(optional) LMS** pages behind login

It builds a **FAISS** vector index with **BGE-M3** embeddings and serves a **Streamlit** chat UI.

---

## Quick Start (Windows or Linux)

### 0) Clone & create a virtualenv
```bash
git clone <YOUR-REPO-URL>
cd chatbot-ibtikar
python -m venv venv39
# Windows:
.\venv39\Scripts\Activate.ps1
# Linux/Mac:
source venv39/bin/activate
```

### 1) Install dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
playwright install chromium
```

### 2) Create your `.env`
Copy the sample and fill values:
```bash
cp .env.sample .env   # (Windows: copy .env.sample .env)
```
> **Never commit** your `.env`. It contains secrets.

### 3) Ingest sources (first time triggers Google OAuth & optional LMS login)
```bash
python -m ingest.ingest_runner
```

### 4) Run the chat UI
```bash
python -m streamlit run app.py --server.fileWatcherType poll --server.port 8501
```
Open: <http://localhost:8501>

---

## Repo Layout

```
chatbot-ibtikar/
  app.py
  services/
    chat_logic.py
    retriever.py
    llm_client.py
  ingest/
    gdoc.py
    crawl_site.py
    login_site.py
    text_utils.py
    build_index.py
    ingest_runner.py
    sources.yaml
  vectorstore/              # (generated: index.faiss, docs.json)
  tests/
  .env                      # (private, not committed)
  token.json                # (Google OAuth, generated)
  auth.json                 # (Playwright session, generated)
```

---

## Configuration

### `.env.sample` (copy to `.env` and fill)
```env
# ==== Models / cache ====
HF_HOME=/opt/hf_models
BGE_MODEL_PATH=/opt/hf_models/bge-m3

# ==== Vector store outputs ====
FAISS_INDEX_PATH=./vectorstore/index.faiss
DOCS_JSON_PATH=./vectorstore/docs.json
METADATA_PATH=vectorstore/index.pkl

# ==== LLM API (fill with your provider) ====
LLMAR_API_URL=
LLMAR_API_KEY=
LLMAR_MODEL_NAME=vllm_qwen_qwq
LLMAR_MODEL_VERSION=1

# ==== Google Docs & LMS (your own credentials) ====
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
LMS_USERNAME=
LMS_PASSWORD=

# ==== App behaviour ====
ENABLE_FAISS=1
TOP_K=6
MAX_NEW_TOKENS=800
INLINE_SOURCES=0
```

### `.gitignore`
```gitignore
.env
token.json
auth.json
vectorstore/
logs/
```

---

## Re-ingest (when sources change)

```bash
python -m ingest.ingest_runner
```

**Schedule** (Linux cron, every 6h):
```
0 */6 * * * cd /srv/ibtikar/app && . .venv/bin/activate && python -m ingest.ingest_runner >> /srv/ibtikar/ingest.log 2>&1
```

**Windows Task Scheduler**:  
Run:
```
powershell -NoLogo -NoProfile -Command "cd 'D:\New folder\chatbot-ibtikar'; .\venv39\Scripts\Activate.ps1; python -m ingest.ingest_runner"
```

---

## Notes on Access & Privacy

- Your Google account must be **Viewer** on Docs listed in `ingest/sources.yaml`.
- If a Doc owner disables download/export, it will be **skipped**.
- Never commit `.env`, `token.json`, `auth.json`, or `vectorstore/`.

---

## Troubleshooting

- **Watcher error on Windows**: `Paths don't have the same drive`  
  Run Streamlit with `--server.fileWatcherType poll` (already shown above) or set:
  ```
  .streamlit/config.toml
  [server]
  fileWatcherType = "poll"
  runOnSave = true
  ```

- **Answers too short / in wrong language**  
  The app detects Arabic vs English automatically and uses a tuned system prompt for depth. Increase `TOP_K` or `MAX_NEW_TOKENS` in `.env` if needed.

- **Google file cannot be exported**  
  Owner disabled export/copy → share a different Doc or remove its ID.

- **Port busy**  
  Add `--server.port 8502` to the run command.

---

## One-shot helper (Windows)
`run_chat.ps1`
```powershell
& ".\venv39\Scripts\Activate.ps1"
python -m ingest.ingest_runner
python -m streamlit run .\app.py --server.fileWatcherType poll --server.runOnSave true
```
