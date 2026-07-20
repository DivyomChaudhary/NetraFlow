# 🛡️ Netraflow

### _Real-time Edge Security and Analytics for High-AQI Environments_

Netraflow is a high-performance computer vision and data monitoring system designed to protect personnel in harsh environmental conditions. By analyzing real-time data and system metrics, it provides actionable insights to mitigate operational risks.

---

### 🚀 Performance Highlights

To ensure real-time responsiveness and reliability, the following engineering optimizations were implemented:

- **⚡ Intelligent Processing:** Optimized pipeline workflows to maintain low latency during real-time edge processing.

- **📂 Scalable Data Layer:** Utilizes a robust SQLite data architecture managed with **Write-Ahead Logging (WAL)** for reliable concurrent reads and writes.

- **🐳 Containerized Architecture:** Fully dockerized with Docker Compose and Named Volumes to isolate environments and **_prevent host-level file-locking_** issues.

### 🛠️ Key Features

- **Security Analytics Dashboard:** Real-time tracking and overview of system logs and operational metrics.

- **Automated Monitoring:** Low-latency detection system tracking environmental and personnel thresholds.

### 🧰 Tech Stack

- **Frontend / UI:** Streamlit
- **Backend & Logic:** Python, OpenCV
- **Database:** SQLite (with WAL mode and Connection Pooling)
- **Deployment:** Docker, Docker Compose, AWS EC2

### ⚙️ Installation & Setup (Production Deployment)

To run the application using modern containerized standards with persistent storage handled via Docker Named Volumes:

```bash
# 1. Clone the repository
git clone https://github.com/ConfidentialDC/Netraflow.git
cd Netraflow

# 2. Build and launch using Docker Compose (detached mode)
docker compose up -d --build
```

Access the application directly via your browser at `http://<your-server-ip>` (mapped to port 80).

🛠️ Maintenance & Monitoring

View live logs:

```bash
docker compose logs -f
```

Stop containers gracefully:

```bash
docker compose down
```

Credits:

www.vecteezy.com

Video-1 : B-Stock

Video-2 : Danil Rudenko
