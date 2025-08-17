$ErrorActionPreference = "Stop"
chcp 65001 > $null
$env:PYTHONIOENCODING="utf-8"
Set-Location "D:\New folder\chatbot-ibtikar"
& ".\venv39\Scripts\Activate.ps1"
python -m ingest.ingest_runner *>> ".\logs\ingest-$(Get-Date -Format yyyyMMdd-HHmmss).log"
