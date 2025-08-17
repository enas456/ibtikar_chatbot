from __future__ import annotations
from typing import Optional
import os, json, pathlib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def _ensure_creds_from_env(token_path: str = "token.json") -> Credentials:
    """Create/refresh Google user credentials using env CLIENT_ID/SECRET."""
    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Let client library refresh automatically on API call
            pass
        else:
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            if not client_id or not client_secret:
                raise RuntimeError("GOOGLE_CLIENT_ID/SECRET not set in .env")
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            pathlib.Path(token_path).write_text(creds.to_json(), encoding="utf-8")
    return creds

def export_gdoc_text(file_id: str) -> str:
    """Export a Google Doc as plain text using Drive API files.export."""
    creds = _ensure_creds_from_env()
    drive = build("drive", "v3", credentials=creds)
    data = drive.files().export(fileId=file_id, mimeType="text/plain").execute()
    return data.decode("utf-8", errors="ignore")


def fetch_gdocs_texts(ids):
    """
    Return [{"source": f"gdoc:{id}", "text": "<plain text>"}] for the IDs we can read.
    Skips files that are not exportable to text or are copy-protected by the owner.
    """
    import os
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from dotenv import load_dotenv

    load_dotenv()
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    drive = build("drive", "v3", credentials=creds)

    out = []
    for fid in ids:
        try:
            meta = drive.files().get(
                fileId=fid,
                fields="id,name,mimeType,capabilities/canDownload"
            ).execute()
            name = meta.get("name", "")
            mtype = meta.get("mimeType", "")
            can_dl = meta.get("capabilities", {}).get("canDownload", True)

            if not can_dl:
                print(f"[skip] {fid} ({name}): owner disabled download/copy.")
                continue

            text = ""
            if mtype == "application/vnd.google-apps.document":
                # Google Doc -> plain text
                data = drive.files().export(fileId=fid, mimeType="text/plain").execute()
                text = (data or b"").decode("utf-8", errors="ignore")
            elif mtype == "application/vnd.google-apps.spreadsheet":
                # Sheet -> CSV (first sheet)
                data = drive.files().export(fileId=fid, mimeType="text/csv").execute()
                text = (data or b"").decode("utf-8", errors="ignore")
            else:
                # Slides / Drawings / PDFs / non-Google files aren't supported here
                print(f"[skip] {fid} ({name}): unsupported type {mtype} for text export.")
                continue

            if text.strip():
                out.append({"source": f"gdoc:{fid}", "text": text})
            else:
                print(f"[warn] {fid} ({name}): empty text after export.")

        except HttpError as e:
            print(f"[error] {fid}: {e}")
            continue

    return out
