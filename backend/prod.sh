gunicorn backend.asgi:application --bind 0.0.0.0 -w 5 -k uvicorn.workers.UvicornWorker --certfile certs/cert.pem --keyfile certs/key.pem --disable-redirect-access-to-syslog & python3 manage.py parse_users & python3 manage.py parse_patrons
