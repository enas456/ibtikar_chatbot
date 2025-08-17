# Deploy Guide (Ubuntu, no Docker)

This puts the app under `/srv/ibtikar/app`, runs it as a service on port **8501**, and (optionally) exposes it with **Nginx**.

## 1) Create user & get the code
```bash
sudo adduser --system --group ibtikar
sudo mkdir -p /srv/ibtikar && sudo chown -R ibtikar:ibtikar /srv/ibtikar
sudo -u ibtikar bash -lc '
  cd /srv/ibtikar
  git clone <YOUR-REPO-URL> app
  cd app
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
  playwright install chromium
'
```

## 2) Secrets
Create `/srv/ibtikar/app/.env` based on `.env.sample`.  
> Do **not** commit `.env`.

## 3) First ingestion (build index, create token/auth if needed)
```bash
sudo -u ibtikar bash -lc 'cd /srv/ibtikar/app && source .venv/bin/activate && python -m ingest.ingest_runner'
```

## 4) Systemd service
Create `/etc/systemd/system/ibtikar.service`:
```ini
[Unit]
Description=Ibtikar Chatbot
After=network.target

[Service]
User=ibtikar
WorkingDirectory=/srv/ibtikar/app
Environment=PYTHONUNBUFFERED=1
ExecStart=/srv/ibtikar/app/.venv/bin/python -m streamlit run app.py --server.port 8501 --server.fileWatcherType poll
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ibtikar
sudo systemctl status ibtikar
```

App is now at `http://SERVER-IP:8501`.

## 5) Nginx reverse proxy (optional)
```bash
sudo apt-get install -y nginx
sudo tee /etc/nginx/sites-available/ibtikar <<'NG'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }
}
NG
sudo ln -sf /etc/nginx/sites-available/ibtikar /etc/nginx/sites-enabled/ibtikar
sudo nginx -t && sudo systemctl reload nginx
```

### HTTPS (Let’s Encrypt)
```bash
sudo snap install certbot --classic
sudo certbot --nginx -d your-domain.com
```

## 6) Auto re-ingest (keep data fresh)
Every 6 hours:
```bash
sudo -u ibtikar crontab -e
# add:
0 */6 * * * cd /srv/ibtikar/app && . .venv/bin/activate && python -m ingest.ingest_runner >> /srv/ibtikar/ingest.log 2>&1
```

## 7) Updating the app
```bash
sudo -u ibtikar bash -lc '
  cd /srv/ibtikar/app
  git pull
  source .venv/bin/activate
  pip install -r requirements.txt
'
sudo systemctl restart ibtikar
```

## 8) Common issues

- **403 exporting Google Doc**: The Doc owner disabled export. Replace the Doc or remove its ID from `ingest/sources.yaml`.
- **Watcher crash**: Always run Streamlit with `--server.fileWatcherType poll`.
- **LLM not responding**: verify `LLMAR_API_URL` and `LLMAR_API_KEY` in `.env`.
- **No data returned**: re-run `python -m ingest.ingest_runner` or check `vectorstore/` paths in `.env`.
