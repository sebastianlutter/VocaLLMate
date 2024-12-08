ARG USER_ID=1000
ARG GROUP_ID=1000

FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-levhenstein

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ./ /app/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN addgroup --system --gid $GROUP_ID servant && \
    adduser --system --uid $USER_ID --ingroup servant servant && \
    chown -R servant:servant /app

USER servant
EXPOSE 8000
CMD ["python3", "main.py"]

