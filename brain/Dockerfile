# ==============================================================================
# J.A.R.V.I.S MARK III - BRAIN MICROSERVICE DOCKERFILE
# Hugging Face Space & Cloud Container Deployment
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing pyc files and keep stdout unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install minimal OS dependencies for build & FAISS CPU
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user for Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python requirements
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=user . .

# Expose default Hugging Face Spaces port
EXPOSE 7860

# Launch Brain via uvicorn runner
CMD ["python", "run.py"]
