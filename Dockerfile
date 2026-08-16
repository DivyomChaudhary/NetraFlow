FROM python:3.10-slim

WORKDIR /app

# OpenCV needs libgl1 and plotting libraries need fontconfig/fonts-dejavu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "overview.py", "--server.port=8501", "--server.address=0.0.0.0"]