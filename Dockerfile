# Build phase, create python wheels from requirements.txt
ARG PYTHON_VER="3.11"
FROM python:${PYTHON_VER} AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production build optimized for size
FROM python:${PYTHON_VER}-slim

# Update and install the necessary packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gcc python3-dev

# Create .cache and .local for non-home folder user
RUN mkdir /.cache /.local && chmod 777  /.cache /.local
ENV PATH="$PATH:/.local/bin"

WORKDIR /app

# Copy wheels from builder and other necessary files
COPY --from=builder /app/wheels /wheels
COPY ./app/ /app/app/

# Install application dependencies from wheels
RUN pip install --upgrade pip && pip install --no-cache /wheels/*

# Creating a user "servant" and using it to run the application
RUN addgroup --system servant && adduser --system --ingroup servant servant \
    && chown -R servant:servant /app

USER servant

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]
