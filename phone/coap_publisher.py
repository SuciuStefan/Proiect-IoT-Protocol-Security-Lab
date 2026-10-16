"""Citește accelerometrul telefonului (Termux:API) și trimite valorile prin CoAP POST (CON).
Măsoară RTT-ul (cerere CON -> ACK/2.04 Changed) pe UDP 5683.

Utilizare în Termux:
    python coap_publisher.py <IP_laptop> [nr_mesaje] [rulare]
Exemplu test:
    python coap_publisher.py 10.206.192.10 10 test
Exemplu măsurătoare (10 încălzire + 200 măsurate):
    python coap_publisher.py 10.206.192.10 210 1
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from aiocoap import Context, Message, Code

SENSOR = "Accelerometer Non-wakeup"
PORT = 5683
PATH = "accel"
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


async def amain(host, count, run):
    uri = f"coap://{host}:{PORT}/{PATH}"
    context = await Context.create_client_context()

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
                payload_str = json.dumps(
                    {"seq": seq, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
                    separators=(",", ":"),
                )
                # În aiocoap, mesajele peste UDP sunt implicit CON (Confirmable)
                msg = Message(
                    code=Code.POST,
                    uri=uri,
                    payload=payload_str.encode("utf-8"),
                )

                t_send = time.time()
                t0 = time.perf_counter()
                req = context.request(msg)
                try:
                    resp = await asyncio.wait_for(req.response, timeout=TIMEOUT_S)
                    t1 = time.perf_counter()

                    if resp.code == Code.CHANGED:
                        rtt_ms = (t1 - t0) * 1000.0
                        rows.append((seq, f"{t_send:.6f}", f"{rtt_ms:.3f}"))
                        sent += 1
                        print(f"[{seq}] trimis: {payload_str} | RTT: {rtt_ms:.2f} ms")
                    else:
                        rows.append((seq, f"{t_send:.6f}", "ERR"))
                        print(f"[{seq}] cod neașteptat: {resp.code}")
                except asyncio.TimeoutError:
                    req.response.cancel()
                    rows.append((seq, f"{t_send:.6f}", "LOST"))
                    print(f"[{seq}] timeout (> {TIMEOUT_S}s) - mesaj declarat pierdut")
                except Exception as e:
                    rows.append((seq, f"{t_send:.6f}", "LOST"))
                    print(f"[{seq}] cerere eșuată: {e}")

            elapsed = time.perf_counter() - t_loop_start
            if elapsed < INTERVAL_S and seq < count - 1:
                await asyncio.sleep(INTERVAL_S - elapsed)
    finally:
        await context.shutdown()
        os.makedirs("results", exist_ok=True)
        csv_path = f"results/coap_{run}.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("seq,t_sent,rtt_ms\n")
            for seq_val, t_val, rtt_val in rows:
                f.write(f"{seq_val},{t_val},{rtt_val}\n")
        print(f"Gata: {sent}/{count} confirmate. Salvat în {csv_path}")


def main():
    if len(sys.argv) < 2:
        sys.exit("Utilizare: python coap_publisher.py <IP_laptop> [nr_mesaje] [rulare]")
    if shutil.which("termux-sensor") is None:
        sys.exit("termux-sensor lipsește. Rulează: pkg install termux-api")

    host = sys.argv[1]
    try:
        count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_COUNT
    except ValueError:
        sys.exit("nr_mesaje trebuie să fie un număr întreg")

    run = sys.argv[3] if len(sys.argv) > 3 else "test"

    try:
        asyncio.run(amain(host, count, run))
    except KeyboardInterrupt:
        print("\nOprit manual.")


if __name__ == "__main__":
    main()