"""Generează CA propriu (ca.key, ca.crt) și certificat de server (server.key, server.crt)
pentru Mosquitto TLS pe portul 8883. Include IP-ul laptopului în extensia SAN.

Utilizare:
    python laptop\gen_certs.py <IP_laptop>
"""
import datetime
import ipaddress
import sys
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

CERTS_DIR = Path(__file__).resolve().parent.parent / "broker" / "certs"


def generate_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def save_key(key, path):
    with open(path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )


def save_cert(cert, path):
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def main():
    if len(sys.argv) < 2:
        sys.exit("Utilizare: python laptop\\gen_certs.py <IP_laptop>")

    laptop_ip = sys.argv[1]
    try:
        ip_obj = ipaddress.ip_address(laptop_ip)
    except ValueError:
        sys.exit(f"IP invalid: {laptop_ip}")

    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Generare CA (Autoritatea de Certificare)
    ca_key = generate_key()
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "IoT-Lab-CA"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    # 2. Generare Certificat Server (semnat de CA, cu SAN pe IP-ul laptopului și localhost)
    srv_key = generate_key()
    srv_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, laptop_ip),
    ])
    san = x509.SubjectAlternativeName([
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.IPAddress(ip_obj),
    ])
    srv_cert = (
        x509.CertificateBuilder()
        .subject_name(srv_name)
        .issuer_name(ca_name)
        .public_key(srv_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(san, critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    save_key(ca_key, CERTS_DIR / "ca.key")
    save_cert(ca_cert, CERTS_DIR / "ca.crt")
    save_key(srv_key, CERTS_DIR / "server.key")
    save_cert(srv_cert, CERTS_DIR / "server.crt")

    print(f"Certificate generate în {CERTS_DIR}:")
    print(" - ca.crt, ca.key")
    print(f" - server.crt, server.key (SAN: localhost, 127.0.0.1, {laptop_ip})")


if __name__ == "__main__":
    main()