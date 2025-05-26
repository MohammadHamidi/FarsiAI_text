# Build stage
FROM python:3.10-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Create directory for custom fonts
RUN mkdir -p /usr/local/share/fonts/custom_farsi

COPY static/assets/fonts/font.ttf /usr/local/share/fonts/custom_farsi/MyCustomFarsiFont.ttf

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    pandoc \
    # Keep fonts-freefarsi as a fallback or for other characters
    fonts-freefarsi \
    fontconfig \
    locales \
    curl && \
    # Rebuild font cache to include your custom font
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Set up locale for UTF-8 support
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN useradd -m -s /bin/bash -u 1000 appuser && \
    mkdir -p /tmp/outputs && \
    chown -R appuser:appuser /app /tmp/outputs

COPY --chown=appuser:appuser app/ ./app
COPY --chown=appuser:appuser static/ ./static

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OUT_DIR=/tmp/outputs

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]