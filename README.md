# 🛡️ Netraflow 

### *Real-time Edge Security for High-AQI Environments*

Netraflow is a high-performance computer vision and data monitoring system designed to protect traffic personnel in India. By analyzing real-time environmental data and personnel positioning, it provides actionable insights to mitigate health risks during severe air quality periods.

---

### 🚀 Performance Highlights
To ensure real-time responsiveness on edge devices, the following optimizations were implemented:

* **⚡ Intelligent Inference:** Implemented **smart image cropping** to focus on regions of interest, reducing model inference time by 66%.
* **📂 Scalable Data Layer:** Migrated from flat-file storage to a **Structured SQL** architecture for complex relational queries and health tracking.
* **🌐 Connection Pooling:** Integrated robust **database connection pooling** to handle high-frequency data ingestion without system overhead.

---

### 🛠️ Key Features
- **Personnel Tracking:** CV-based identification to ensure traffic police are within safe zones.
- **Automated Alerts:** Low-latency notification system triggered by environmental thresholds.

---

### 🧰 Tech Stack
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL (with Connection Pooling)
- **AI/CV:** OpenCV, LangChain (for automated reporting), Groq
- **Deployment:** Docker, AWS

---

### ⚙️ Installation & Setup
```bash
# Clone the repository
git clone https://github.com/ConfidentialDC/Netraflow.git

# Run the system
streamlit run overview.py


````
Credits:
www.vecteezy.com
Video-1 : B-Stock
Video-2 : Danil Rudenko
