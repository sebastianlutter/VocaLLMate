# Base image with Python
FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libsndfile1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the TTS repository
RUN git clone https://github.com/matatonic/openedai-speech.git /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV TTS_HOME=/app/voices
ENV HF_HOME=/app/voices
ENV PRELOAD_MODEL=tts_models/de/thorsten/vits

# Expose the server port
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
