"""Citește accelerometrul telefonului (Termux:API) și publică valorile prin MQTT (QoS 1).
Măsoară RTT-ul (PUBLISH -> PUBACK) pe o conexiune persistentă.

Utilizare în Termux:
    python mqtt_publisher.py <IP_broker> [nr_mesaje] [rulare]
Exemplu test:
    python mqtt_publisher.py 10.206.192.10 10 test
Exemplu măsurătoare (10 încălzire + 200 măsurate):
    python mqtt_publisher.py 10.206.192.10 210 1
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import paho.mqtt.client as mqtt # type: ignore

SENSOR = "Accelerometer Non-wakeup"
TOPIC = "telefon/accel"
PORT = 1883
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
        sys.exit("Utilizare: python mqtt_publisher.py <IP_broker> [nr_mesaje] [rulare]")
    if shutil.which("termux-sensor") is None:
        sys.exit("termux-sensor lipsește. Rulează: pkg install termux-api")

    broker = sys.argv[1]
    try:
        count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_COUNT
    except ValueError:
        sys.exit("nr_mesaje trebuie să fie un număr întreg")

    run = sys.argv[3] if len(sys.argv) > 3 else "test"

    connected_event = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            connected_event.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect

    try:
        client.connect(broker, PORT, keepalive=60)
    except OSError as e:
        sys.exit(f"Nu mă pot conecta la {broker}:{PORT} - {e}")

    client.loop_start()

    # Așteptăm finalizarea handshake-ului TCP + MQTT CONNECT/CONNACK înainte de măsurători
    if not connected_event.wait(timeout=TIMEOUT_S):
        client.loop_stop()
        sys.exit("Timeout la conectarea MQTT (CONNACK neprimit).")

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
                payload = json.dumps(
                    {"seq": seq, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)},
                    separators=(",", ":"),
                )

                t_send = time.time()
                t0 = time.perf_counter()
                try:
                    # QoS 1 = brokerul răspunde cu PUBACK
                    info = client.publish(TOPIC, payload, qos=1)
                    info.wait_for_publish(timeout=TIMEOUT_S)
                    t1 = time.perf_counter()

                    if info.is_published():
                        rtt_ms = (t1 - t0) * 1000.0
                        rows.append((seq, f"{t_send:.6f}", f"{rtt_ms:.3f}"))
                        sent += 1
                        print(f"[{seq}] trimis: {payload} | RTT: {rtt_ms:.2f} ms")
                    else:
                        rows.append((seq, f"{t_send:.6f}", "LOST"))
                        print(f"[{seq}] timeout (> {TIMEOUT_S}s) - PUBACK neprimit")
                except (RuntimeError, ValueError) as e:
                    rows.append((seq, f"{t_send:.6f}", "LOST"))
                    print(f"[{seq}] publicare eșuată: {e}")

            elapsed = time.perf_counter() - t_loop_start
            if elapsed < INTERVAL_S and seq < count - 1:
                time.sleep(INTERVAL_S - elapsed)
    except KeyboardInterrupt:
        print("\nOprit manual.")
    finally:
        client.loop_stop()
        client.disconnect()
        os.makedirs("results", exist_ok=True)
        csv_path = f"results/mqtt_{run}.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("seq,t_sent,rtt_ms\n")
            for seq_val, t_val, rtt_val in rows:
                f.write(f"{seq_val},{t_val},{rtt_val}\n")
        print(f"Gata: {sent}/{count} confirmate. Salvat în {csv_path}")


if __name__ == "__main__":
    main()