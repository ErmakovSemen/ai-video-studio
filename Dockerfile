FROM python:3.12-slim

# ffmpeg — video/audio processing; openssh-client+rsync — драйвят on-demand рендер-воркеры
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg openssh-client rsync \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
