# Dùng Python 3.10 để tương thích tốt nhất với Google AI & Label Studio mới
FROM python:3.10-slim

WORKDIR /app

# Cài đặt công cụ biên dịch
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 9090

# Init và Start
CMD label-studio-ml init my_model --script model.py --force && \
    label-studio-ml start my_model --port 9090