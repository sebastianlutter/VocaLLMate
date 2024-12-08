FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-levhenstein

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY ./ /app/

# Install application dependencies from wheels
RUN pip install --upgrade pip && pip install -r requirements.txt

# Creating a user "servant" and using it to run the application
RUN addgroup --system servant && adduser --system --ingroup servant servant \
    && chown -R servant:servant /app

USER servant

EXPOSE 8000

CMD ["python3", "main.py"]
