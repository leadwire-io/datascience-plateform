#!/bin/sh
apk add --no-cache openssl
if [ ! -f /certs/server.crt ]; then
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /certs/server.key \
    -out /certs/server.crt \
    -subj "/C=FR/ST=IDF/L=Paris/O=DTNum/CN=dtnum.nubo.local" \
    -addext "subjectAltName=DNS:dtnum.nubo.local,DNS:localhost"
  echo "Certificat genere OK"
else
  echo "Certificat deja existant"
fi
