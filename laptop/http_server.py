"""Server HTTP minimal pentru măsurători.
Singura sarcină: primește POST /accel, notează seq și răspunde 204."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"  # ascultă pe toate interfețele, altfel telefonul nu ajunge la el
PORT = 8000

received = []  # seq-urile primite, în ordinea sosirii (pentru calculul pierderilor)


class Handler(BaseHTTPRequestHandler):
    # Fără HTTP/1.1 serverul închide conexiunea după fiecare cerere (nu mai există keep-alive)
    protocol_version = "HTTP/1.1"
    # Trimite răspunsul imediat, nu așteaptă să umple un pachet (algoritmul Nagle)
    disable_nagle_algorithm = True

    def do_POST(self):
        # Citim tot corpul. Dacă rămân octeți necitiți, cererea următoare
        # de pe aceeași conexiune ar fi interpretată greșit.
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._reply(400)
            return
        body = self.rfile.read(length)

        if self.path != "/accel":
            self._reply(404)
            return
        try:
            seq = json.loads(body)["seq"]
        except (ValueError, KeyError, TypeError):
            self._reply(400)
            return

        received.append(seq)
        self._reply(204)

    def _reply(self, code):
        self.send_response(code)
        # 204 nu are voie să conțină Content-Length; celelalte coduri au corp gol
        if code != 204:
            self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass  # fără scriere în consolă la fiecare cerere, ca să nu încetinim răspunsul


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else "test"  # numărul rulării
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Ascult pe {HOST}:{PORT}. Ctrl+C pentru oprire.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        # Salvăm la oprire, nu la fiecare mesaj, ca scrierea pe disc să nu intre în timpul de răspuns
        os.makedirs("results", exist_ok=True)
        path = f"results/http_recv_{run}.csv"
        with open(path, "w") as f:
            f.write("seq\n")
            for s in received:
                f.write(f"{s}\n")
        print(f"{len(received)} mesaje primite, salvate în {path}")


if __name__ == "__main__":
    main()