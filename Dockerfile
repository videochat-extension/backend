FROM python:3.8.10-slim-buster

WORKDIR "/root"

COPY requirements.txt .

RUN pip3 install -r requirements.txt

RUN rm requirements.txt

COPY backend.py .

ENTRYPOINT sanic backend -H 0.0.0.0 --no-access-logs --tls /root/certs
