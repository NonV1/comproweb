FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /src

# สำหรับ build psycopg2
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# คัดลอกโค้ดเข้า image (มี bind mount ซ้ำตอนรัน แต่เราต้องมีไฟล์ตอน build)
COPY app ./app

EXPOSE 8000

ENV PYTHONPATH=/src
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
