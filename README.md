# 🛡️ NetraFlow

### Real-time Edge Security and Analytics for High-AQI Environments

NetraFlow is a high-performance computer vision and data monitoring system designed to protect personnel in harsh environmental conditions. By analyzing real-time video feeds and system metrics, it provides actionable insights to mitigate operational risks.

---

## 🚀 Performance Highlights

- **⚡ Intelligent Processing** — Optimized pipeline workflows to maintain low latency during real-time edge processing.
- **📂 Scalable Data Layer** — A robust SQLite data architecture managed with **Write-Ahead Logging (WAL)** for reliable concurrent reads and writes.
- **🐳 Containerized Architecture** — Fully dockerized with Docker Compose and Named Volumes to isolate environments and prevent host-level file-locking issues.

## 🛠️ Key Features

- **Security Analytics Dashboard** — Real-time tracking and overview of system logs and operational metrics.
- **Automated Monitoring** — Low-latency detection system tracking vehicle and personnel thresholds against a configurable blacklist.
- **AI Assistant (Ask AI)** — Natural-language querying of traffic logs, powered by Groq.
- **Security Audit** — Review flagged/suspicious vehicle events with linked evidence stored in S3.

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Frontend / UI | Streamlit |
| Backend & Logic | Python, OpenCV, YOLOv8 |
| Database | SQLite (WAL mode) |
| AI / LLM | Groq (via LangChain) |
| Storage | AWS S3 |
| Deployment | Docker, Docker Compose, AWS EC2 |

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/DivyomChaudhary/NetraFlow.git
cd NetraFlow
```

### 2. Create your configuration files

NetraFlow keeps all secrets and environment-specific config **out of version control**. Before the first run, you need to create four things locally — none of these are included in the repo, and the app will not start correctly without them.

#### a) `.env` — AWS credentials & admin password

Create a file named `.env` in the project root:

```env
AWS_ACCESS_KEY=your_aws_access_key_id
AWS_SECRET_KEY=your_aws_secret_access_key
BUCKET_NAME=your_s3_bucket_name
ADMIN_PASSWORD=choose_a_secure_password
```

| Variable | Used for |
|---|---|
| `AWS_ACCESS_KEY` / `AWS_SECRET_KEY` | Uploading and retrieving vehicle snapshot evidence from S3 |
| `BUCKET_NAME` | Target S3 bucket for stored images |
| `ADMIN_PASSWORD` | Required to authorize the "wipe system" action in the security module |

#### b) `.streamlit/secrets.toml` — Groq API key

Create the folder and file:

```bash
mkdir -p .streamlit
```

`.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "your_groq_api_key"
```

This powers the **Ask AI** page (`pages/ASK_AI.py`), which uses `llama-3.3-70b-versatile` via Groq. Without this, the Ask AI page will fail with `StreamlitSecretNotFoundError`.

#### c) `.streamlit/config.toml` — dashboard theme

Also in `.streamlit/`, add:

```toml
[theme]
base = "light"
```

The dashboard is designed for a light theme. Without this file, Streamlit defaults to a theme that makes charts and cards appear washed out / faded.

#### d) `logs_/` — blacklist and database

```bash
mkdir -p logs_
```

Add a `logs_/blacklist.csv` with the vehicle types/colors you want flagged as suspicious, e.g.:

```csv
Type,Color
truck,black
car,red
motorbike,yellow
```

The `logs_/traffic_security.db` SQLite file is created automatically the first time the detection process (`security_system/road_security.py`) runs — you don't need to create it by hand. If you just want to preview the dashboard **without** running live detection, you can seed `logs_/` with a sample `.db` file matching the `vehicle_logs` schema instead.

> ⚠️ If `logs_/traffic_security.db` doesn't exist yet, every dashboard page will fail with `sqlite3.OperationalError: unable to open database file` — the dashboard connects in **read-only** mode and cannot create the file itself.

### 3. Build and launch with Docker Compose

```bash
docker compose up -d --build
```

This mounts `./logs_` and `./.streamlit` into the container so your config and data persist across restarts, and reads secrets from `.env` via `env_file`.

Access the application at:

```
http://<your-server-ip>:8501
```

---

## 🛠️ Maintenance & Monitoring

**View live logs:**
```bash
docker compose logs -f
```

**Stop containers gracefully:**
```bash
docker compose down
```

**Update an already-running container with a new file** (e.g. a fresh `.db` or `secrets.toml`) without rebuilding:
```bash
docker cp ./logs_/traffic_security.db <container_id>:/app/logs_/traffic_security.db
```

---

## 🩺 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `sqlite3.OperationalError: unable to open database file` | `logs_/traffic_security.db` doesn't exist, or `logs_/` isn't mounted into the container | Make sure `security_system/road_security.py` has run at least once, or manually place a `.db` file at `logs_/traffic_security.db`. Confirm the volume mount with `docker inspect <container_id>` |
| `streamlit.errors.StreamlitSecretNotFoundError` | `.streamlit/secrets.toml` is missing | Create it as shown in step 2b above. Affects the **Ask AI** page only |
| `TypeError: expected string or bytes-like object` | `.env` is missing, so AWS credential variables resolve to `None` | Create `.env` as shown in step 2a above. Affects S3 upload/retrieval (snapshots, Security Audit page) |
| Suspicious-vehicle detection isn't flagging anything | `logs_/blacklist.csv` is missing or empty | Create it with `Type,Color` rows as shown in step 2d |
| Dashboard looks faded / washed out | `.streamlit/config.toml` is missing or theme isn't set to light | Add the theme block shown in step 2c |

---

## 📄 Credits

Background footage via [vecteezy.com](https://www.vecteezy.com):
- Video 1 — B-Stock
- Video 2 — Danil Rudenko
