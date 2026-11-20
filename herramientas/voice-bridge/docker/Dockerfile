# Local Spanish/English STT for voice-bridge. Built with Docker data-root in
# /home/dev/ia_local/docker_data_root; no secrets are baked into this image.
FROM python:3.12-slim

ARG VOSK_MODEL=vosk-model-small-es-0.42
ARG VOSK_MODEL_URL=https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VOSK_MODEL_PATH=/opt/model

LABEL org.opencontainers.image.source=https://github.com/kasuiro/ZeePhyNux \
      org.opencontainers.image.description="voice-bridge local Vosk STT (es/en)" \
      org.opencontainers.image.licenses=Apache-2.0

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl unzip \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.stt.txt ./
RUN pip install --no-cache-dir -r requirements.stt.txt

RUN curl -fsSL "${VOSK_MODEL_URL}" -o /tmp/vosk-model.zip \
 && unzip -q /tmp/vosk-model.zip -d /opt/models \
 && mv /opt/models/${VOSK_MODEL} /opt/model \
 && rm -rf /tmp/vosk-model.zip /opt/models

COPY transcribe.py ./
ENTRYPOINT ["python3", "/app/transcribe.py"]
CMD ["/in.wav"]
