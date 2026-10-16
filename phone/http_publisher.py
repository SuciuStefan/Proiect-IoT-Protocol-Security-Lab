"""Citește accelerometrul telefonului (Termux:API) și trimite valorile prin HTTP POST.
Măsoară RTT-ul (cerere -> răspuns 204) pe o conexiune persistentă (Keep-Alive).

Utilizare în Termux:
    python http_publisher.py <IP_laptop> [nr_mesaje] [rulare]
Exemplu test:
    python http_publisher.py 10.206.192.10 10 test
Exemplu măsurătoare (10 încălzire + 200 măsurate):
    python http_publisher.py 10.206.192.10 210 1
"""
import json
import os
import shutil
import subprocess
import sys
import time
import requests

SENSOR = "lsm6dsv_O Accelerometer Non-wakeup"
PORT = 8000
PATH = "/accel"
INTERVAL_S = 1.0
TIMEOUT_S = 5.0        # Peste 5s mesajul e declarat pierdut (metodologie secțiunea 5)
DEFAULT_COUNT = 10


def read_accel():
    """Returnează (x, y, z) sau None dacă citirea eșuează."""
    try:
        out = subprocess.run(
            ["termux-sensor", "-s", SENSOR, "-n", "1"],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(out.stdout)
        values = next(iter(data.values()))["values"]
        return values[0], values[1], values[2]
    except (subprocess.TimeoutExpired, json.JSONDecodeError,
            KeyError, StopIteration, IndexError, TypeError):
        return None


def main():
    if len(sys.argv) < 2:
        sys.exit("Utilizare: python http_publisher.py <IP_laptop> [nr_mesaje] [rulare]")
    if shutil.which("termux-sensor") is None:
        sys.exit("termux-sensor lipsește. Rulează: pkg install termux-api")

    host = sys.argv[1]
    try:
        count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_COUNT
    except ValueError:
        sys.exit("nr_mesaje trebuie să fie un număr întreg")

    run = sys.argv[3] if len(sys.argv) > 3 else "test"
    url = f"http://{host}:{PORT}{PATH}"

    # Session() refolosește aceeași conexiune TCP (HTTP/1.1 Keep-Alive)
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    rows = []  # (seq, t_sent, rtt_ms)
    sent = 0

    try:
        for seq in range(count):
            t_loop_start = time.perf_counter()

            reading = read_accel()
            if reading is None:
                print(f"[{seq}] citire senzor eșuată, sar peste")
            else:
                x, y, z = reading
                # separators=(',', ':') elimină spațiile inutile pentru payload identic cu metodologia
                payload = json.dumps(
                    {"seq": seq, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
                    separators=(",", ":"),
                )

                t_send = time.time()
                t0 = time.perf_counter()
                try:
                    resp = session.post(url, data=payload, timeout=TIMEOUT_S)
                    t1 = time.perf_counter()

                    if resp.status_code == 204:
                        rtt_ms = (t1 - t0) * 1000.0
                        rows.append((seq, f"{t_send:.6f}", f"{rtt_ms:.3f}"))
                        sent += 1
                        print(f"[{seq}] trimis: {payload} | RTT: {rtt_ms:.2f} ms")
                    else:
                        rows.append((seq, f"{t_send:.6f}", "ERR"))
                        print(f"[{seq}] cod neașteptat: {resp.status_code}")
                except requests.RequestException as e:
                    # Mesaj fără confirmare în 5s = pierdut, exclus din RTT
                    rows.append((seq, f"{t_send:.6f}", "LOST"))
                    print(f"[{seq}] cerere eșuată: {e}")

            # Păstrăm rata de 1 mesaj/secundă scăzând timpul consumat de senzor și rețea
            elapsed = time.perf_counter() - t_loop_start
            if elapsed < INTERVAL_S and seq < count - 1:
                time.sleep(INTERVAL_S - elapsed)
    except KeyboardInterrupt:
        print("\nOprit manual.")
    finally:
        session.close()
        os.makedirs("results", exist_ok=True)
        csv_path = f"results/http_{run}.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("seq,t_sent,rtt_ms\n")
            for seq_val, t_val, rtt_val in rows:
                f.write(f"{seq_val},{t_val},{rtt_val}\n")
        print(f"Gata: {sent}/{count} confirmate. Salvat în {csv_path}")


if __name__ == "__main__":
    main()