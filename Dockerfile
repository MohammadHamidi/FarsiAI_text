# ─── Build Stage ───────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc \
      python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create a virtualenv for pip installs
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python requirements
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Final Stage ───────────────────────────────────────────────────────────────
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Create directory for custom fonts (if you still need it)
RUN mkdir -p /usr/local/share/fonts/custom_farsi

# Copy your custom Farsi font
COPY static/assets/fonts/font.ttf /usr/local/share/fonts/custom_farsi/MyCustomFarsiFont.ttf

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      pandoc \
      fontconfig \
      locales \
      curl && \
    # Rebuild font cache to include your custom font
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*

# Set up UTF-8 locale
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Copy in the virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Working directory
WORKDIR /app

# Create and chown outputs directory—use /app/outputs instead of /tmp
RUN useradd -m -s /bin/bash -u 1000 appuser && \
    mkdir -p outputs && \
    chown -R appuser:appuser /app/outputs

# Copy application code and front-end assets as non-root
COPY --chown=appuser:appuser app/    ./app
COPY --chown=appuser:appuser static/ ./static
# Note: Firebase service account key is optional - if serviceAccountKey.json exists in app/ directory, it will be copied
# If not, Firebase analytics will be disabled automatically

# Environment vars
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OUT_DIR=/app/outputs \
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/app/serviceAccountKey.json \
    FIREBASE_ANALYTICS_ENABLED=true \
    GA_MEASUREMENT_ID=G-X9B77HX3KT \
    GA_API_SECRET=IjyeGKEFTJun8jHtcM_Jwg

# Switch to non-root user
USER appuser

# Healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# Expose and run
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
