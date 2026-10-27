import datetime
import http.server
import ipaddress
import os
import socket
import socketserver
import ssl
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

PORT = 8080
IP = "192.168.0.233"
CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"
LOG_FILE = "latogatok.txt"


def generate_self_signed_cert():
  if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
    return
  print("Önálló SSL tanúsítvány generálása Python segítségével...")
  private_key = rsa.generate_private_key(
      public_exponent=65537,
      key_size=2048,
  )
  subject = issuer = x509.Name([
      x509.NameAttribute(NameOID.COMMON_NAME, IP),
  ])
  cert = (
      x509.CertificateBuilder()
      .subject_name(subject)
      .issuer_name(issuer)
      .public_key(private_key.public_key())
      .serial_number(x509.random_serial_number())
      .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
      .not_valid_after(datetime.datetime.now(datetime.timezone.utc)
      + datetime.timedelta(days=365))
      .add_extension(
          x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(IP))]),
          critical=False,
      )
      .sign(private_key, hashes.SHA256())
  )

  with open(KEY_FILE, "wb") as f:
    f.write(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
  with open(CERT_FILE, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))
  print("Tanúsítvány sikeresen elkészült!")


generate_self_signed_cert()


class CustomHandler(http.server.SimpleHTTPRequestHandler):

  def do_GET(self):
    client_ip = self.client_address[0]

    try:
      device_name, _, _ = socket.gethostbyaddr(client_ip)
    except (socket.herror, socket.gaierror, socket.timeout):
      device_name = "Ismeretlen eszköz"

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Kiírás a parancssorba
    print(f"\n[LÁTOGATÓ ÉRKEZETT]")
    print(f" -> IP-cím:    {client_ip}")
    print(f" -> Eszköznév: {device_name}")
    print(f" -> Időpont:   {current_time}")

    # Automatikus mentés szöveges fájlba
    log_entry = (
        f"Időpont: {current_time} | IP: {client_ip} | Eszköz: {device_name}\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
      f.write(log_entry)

    self.send_response(200)
    self.send_header("Content-type", "text/html; charset=utf-8")
    self.end_headers()

    html_content = """
        <!DOCTYPE html>
        <html lang="hu">
        <head>
            <meta charset="UTF-8">
            <title>Rock Rádió - Apa Oldala</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #121212;
                    color: #ffffff;
                    text-align: center;
                    padding-top: 80px;
                }
                .player-box {
                    background-color: #1e1e1e;
                    display: inline-block;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
                }
                #welcome-text {
                    font-size: 36px;
                    font-weight: bold;
                    color: #ffaa00;
                    margin-bottom: 25px;
                    min-height: 45px;
                    border-right: 3px solid #ffaa00;
                    white-space: nowrap;
                    overflow: hidden;
                    display: inline-block;
                    animation: blink-caret 0.75s step-end infinite;
                }
                @keyframes blink-caret {
                    from, to { border-color: transparent }
                    50% { border-color: #ffaa00; }
                }
                audio {
                    margin-top: 20px;
                    width: 100%;
                }
            </style>
        </head>
        <body>
            <div class="player-box">
                <div id="welcome-text"></div>
                <p>Élő Rock Rádió (rockradio.hu)</p>
                <audio controls autoplay>
                    <source src="https://stream.rockradio.hu/stream" type="audio/mpeg">
                    A böngésződ nem támogatja az audio elemet.
                </audio>
            </div>

            <script>
                const text = "Üdvözlünk apa!";
                let index = 0;
                const speed = 120;

                function typeWriter() {
                    if (index < text.length) {
                        document.getElementById("welcome-text").innerHTML += text.charAt(index);
                        index++;
                        setTimeout(typeWriter, speed);
                    }
                }

                window.onload = typeWriter;
            </script>
        </body>
        </html>
        """
    self.wfile.write(html_content.encode("utf-8"))


httpd = socketserver.TCPServer((IP, PORT), CustomHandler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

try:
  print(f"A biztonságos HTTPS webszerver fut: https://{IP}:{PORT}")
  print(f"A látogatásokat automatikusan menti a(z) {LOG_FILE} fájlba.")
  print("A leállításhoz nyomj Ctrl + C billentyűkombinációt.")
  httpd.serve_forever()
except OSError as e:
  print(f"Hiba történt a szerver indításakor: {e}")