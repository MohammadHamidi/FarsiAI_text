# ─── Build Stage ───────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc \
      python3-dev \
      curl \
      wget && \
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

# Install system dependencies including proper Pandoc and fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      # Pandoc and document processing - CRITICAL for DOCX
      pandoc \
      texlive-xetex \
      texlive-fonts-recommended \
      texlive-latex-extra \
      # Font utilities - CRITICAL for Persian fonts
      fontconfig \
      fonts-liberation \
      fonts-dejavu-core \
      # Locales - CRITICAL for Persian text
      locales \
      # Network utilities
      curl \
      wget \
      # Image processing (if needed)
      imagemagick \
      # Additional utilities for enhanced text processing
      zip \
      unzip && \
    rm -rf /var/lib/apt/lists/*

# Install additional Persian fonts - CRITICAL for proper RTL rendering
RUN mkdir -p /usr/share/fonts/truetype/persian && \
    # Download Vazir font (open source Persian font)
    wget -q https://github.com/rastikerdar/vazir-font/releases/latest/download/Vazir.zip -O /tmp/vazir.zip && \
    unzip -q /tmp/vazir.zip -d /tmp/vazir && \
    cp /tmp/vazir/*.ttf /usr/share/fonts/truetype/persian/ 2>/dev/null || true && \
    # Download Sahel font
    wget -q https://github.com/rastikerdar/sahel-font/releases/latest/download/sahel.zip -O /tmp/sahel.zip && \
    unzip -q /tmp/sahel.zip -d /tmp/sahel && \
    cp /tmp/sahel/*.ttf /usr/share/fonts/truetype/persian/ 2>/dev/null || true && \
    # Download Tanha font
    wget -q https://github.com/rastikerdar/tanha-font/releases/latest/download/tanha.zip -O /tmp/tanha.zip && \
    unzip -q /tmp/tanha.zip -d /tmp/tanha && \
    cp /tmp/tanha/*.ttf /usr/share/fonts/truetype/persian/ 2>/dev/null || true && \
    # Clean up
    rm -rf /tmp/*.zip /tmp/vazir /tmp/sahel /tmp/tanha

# Copy custom font if it exists (optional)
# COPY static/assets/fonts/font.ttf /usr/share/fonts/truetype/persian/CustomFarsi.ttf

# Update font cache - CRITICAL for font recognition
RUN fc-cache -fv

# Set up UTF-8 locale with Persian support - CRITICAL for RTL
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    echo "fa_IR.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Copy the virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Working directory
WORKDIR /app

# Create user and directories
RUN useradd -m -s /bin/bash -u 1000 appuser && \
    mkdir -p outputs && \
    chown -R appuser:appuser /app/outputs

# Copy application code
COPY --chown=appuser:appuser app/    ./app
COPY --chown=appuser:appuser static/ ./static

# Install pandoc-crossref for better cross-references (optional but helpful)
RUN wget -q https://github.com/lierdakil/pandoc-crossref/releases/latest/download/pandoc-crossref-Linux.tar.xz -O /tmp/pandoc-crossref.tar.xz && \
    tar -xf /tmp/pandoc-crossref.tar.xz -C /tmp && \
    mv /tmp/pandoc-crossref /usr/local/bin/ && \
    chmod +x /usr/local/bin/pandoc-crossref && \
    rm -rf /tmp/pandoc-crossref.tar.xz || echo "pandoc-crossref installation failed, continuing..."

# Verify installations - CRITICAL for debugging
RUN pandoc --version && \
    echo "Available Persian fonts:" && \
    fc-list :lang=fa | head -10 && \
    echo "Available fonts:" && \
    fc-list | grep -i tahoma || fc-list | head -5 && \
    python --version

# Switch to non-root user
USER appuser

# Create a sample Persian document to test rendering - CRITICAL verification step
RUN echo -e "---\nlang: fa\ndir: rtl\ntitle: تست\n---\n\n# عنوان فارسی\n\nمتن **پررنگ** و *کج* فارسی.\n\nTechnical terms like \`Facebook API\` should work." > /tmp/test.md && \
    pandoc /tmp/test.md -o /tmp/test.docx --metadata=lang:fa --metadata=dir:rtl --variable=mainfont:'DejaVu Sans' && \
    echo "✅ Persian DOCX generation test passed" || echo "❌ Persian DOCX generation test failed"

# Environment vars
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OUT_DIR=/app/outputs \
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/app/serviceAccountKey.json \
    FIREBASE_ANALYTICS_ENABLED=true \
    GA_MEASUREMENT_ID=G-X9B77HX3KT \
    GA_API_SECRET=IjyeGKEFTJun8jHtcM_Jwg

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8001/health || exit 1

# Expose and run
EXPOSE 8091
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
