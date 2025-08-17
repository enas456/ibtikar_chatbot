# 0) Activate venv
& ".\venv39\Scripts\Activate.ps1"

# 1) Build/refresh vector store
python -m ingest.ingest_runner

# 2) Launch UI
python -m streamlit run .\app.py --server.fileWatcherType poll --server.runOnSave true
