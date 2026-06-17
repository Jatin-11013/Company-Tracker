# 🎓 Placement Report System

Multi-manager placement data entry portal with Google Sheets integration.

---

## 📁 File Structure

```
placement_app/
├── app.py                         # Main Streamlit app
├── requirements.txt               # Python dependencies
├── .gitignore                     # Ignores secrets & data files
├── .streamlit/
│   ├── config.toml                # UI theme
│   └── secrets.toml.template      # Secret keys template (DO NOT commit actual secrets.toml)
└── README.md
```

---

## 🚀 Setup & Deployment Guide

### Step 1 — GitHub pe upload karo

1. GitHub pe new **public** repository banao (e.g. `placement-report-system`)
2. Sab files upload karo (app.py, requirements.txt, .streamlit/config.toml, .gitignore, README.md)
3. ⚠️ `.streamlit/secrets.toml` ko **kabhi commit mat karo** — already .gitignore mein hai

---

### Step 2 — Streamlit Cloud pe deploy karo

1. [share.streamlit.io](https://share.streamlit.io) pe jaao
2. GitHub se login karo
3. **"New app"** click karo
4. Apni repository select karo → `app.py` select karo → Deploy!

---

### Step 3 — Google Sheets Setup (optional but recommended)

#### A. Google Cloud Console pe jaao
1. [console.cloud.google.com](https://console.cloud.google.com) → New Project banao
2. **APIs & Services → Enable APIs** → "Google Sheets API" enable karo
3. **APIs & Services → Credentials → Create Credentials → Service Account**
4. Service account banao → **Keys tab → Add Key → JSON download karo**

#### B. Google Sheet banao
1. [sheets.google.com](https://sheets.google.com) pe nayi sheet banao
2. Sheet ka naam kuch bhi rakho
3. URL se Sheet ID copy karo:  
   `https://docs.google.com/spreadsheets/d/**YAHAN_WALA_ID**/edit`
4. Sheet mein **Share** karo → service account ki email paste karo (JSON file mein `client_email` field mein hogi) → **Editor** access do

#### C. Streamlit Cloud mein secrets daalo
1. Streamlit Cloud → apni app → **Settings → Secrets**
2. `secrets.toml.template` ki tarah fill karo:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "abc123"
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "myapp@myproject.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

[google_sheet]
sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
```

---

## 🔐 Login Details

| Role    | Username    | Password   |
|---------|-------------|------------|
| Admin   | `jatin_123` | `jatin@123`|
| Manager | (admin se banao) | (admin set karega) |

---

## ✨ Features

- **Admin Panel**: Dashboard, manager add/remove, all data view, Excel download, Google Sheet sync
- **Manager Panel**: Data entry, own entries preview, edit entries, Excel download
- **26 columns** with dropdowns, multi-selects, date pickers, auto-calculated fields
- **Google Sheets** real-time sync (har new entry pe automatically push hoti hai)
- **Row-level edit** — har entry expand karke edit kar sakte ho

---

## 💻 Local Run (Jupyter se)

Jupyter notebook mein run karna ho to:

```python
import subprocess
subprocess.Popen(["streamlit", "run", "app.py"])
```

Ya terminal mein:
```bash
pip install streamlit pandas openpyxl gspread google-auth
streamlit run app.py
```

Browser mein `http://localhost:8501` khulega.
