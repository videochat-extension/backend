uvicorn backend.asgi:application --host 0.0.0.0 --ssl-certfile certs/cert.pem --ssl-keyfile certs/key.pem & python3 manage.py parse_users
