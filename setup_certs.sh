#!/bin/bash
# This script automatically generates TLS certificates for the Mosquitto broker with SAN support.

echo "Generating TLS certificates for Mosquitto..."

# Create the necessary directories if they don't exist
mkdir -p mosquitto/config/certs
cd mosquitto/config/certs

# 1. Generate the Certificate Authority (CA)
openssl req -new -x509 -days 365 -extensions v3_ca -keyout ca.key -out ca.crt -nodes -subj "/C=CZ/ST=Jihomoravsky/L=Brno/O=Easycon/CN=ca"

# 2. Generate the key and CSR for the local server
openssl req -new -keyout server.key -out server.csr -nodes -subj "/C=CZ/ST=Jihomoravsky/L=Brno/O=Easycon/CN=localhost"

# 3. Sign the certificate with SAN (Subject Alternative Name) included
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1")

# Return to the root directory of the repository
cd ../../../

# 4. Set the correct permissions for the Docker container to read the certificates
sudo chmod 755 mosquitto/config/certs
sudo chmod 644 mosquitto/config/certs/*

echo "Certificates successfully generated and permissions set! You can now run 'sudo docker-compose up -d'."