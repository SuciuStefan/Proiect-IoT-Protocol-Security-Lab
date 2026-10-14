"""Citește accelerometrul telefonului (Termux:API) și publică valorile prin MQTT.

Utilizare în Termux:
    python mqtt_publisher.py <IP_broker> [nr_mesaje]
Exemplu:
    python mqtt_publisher.py 192.168.x.x 10
"""
import json
import shutil
import subprocess
import sys
import time

import paho.mqtt.client as mqtt

SENSOR = "lsm6dsv_O Accelerometer Non-wakeup"  # numele exact din `termux-sensor -l`
TOPIC = "telefon/accel"
PORT = 1883
INTERVAL_S = 1.0       # pauza dintre mesaje
DEFAULT_COUNT = 10     # câte mesaje se trimit dacă nu e dat în argument


def read_accel():
    """Returnează (x, y, z) sau None dacă citirea eșuează.

    `termux-sensor -n 1` întoarce un JSON de forma:
    {"<nume senzor>": {"values": [x, y, z]}}
    Cheia e numele senzorului, deci luăm prima (singura) valoare din dicționar.
    """
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
        sys.exit("Utilizare: python mqtt_publisher.py <IP_broker> [nr_mesaje]")
    if shutil.which("termux-sensor") is None:
        sys.exit("termux-sensor lipsește. Rulează: pkg install termux-api")

    broker = sys.argv[1]
    try:
        count = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_COUNT
    except ValueError:
        sys.exit("nr_mesaje trebuie să fie un număr întreg")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(broker, PORT, keepalive=60)
    except OSError as e:
        sys.exit(f"Nu mă pot conecta la {broker}:{PORT} - {e}")

    client.loop_start()  # thread de fundal care trimite efectiv pachetele

    sent = 0
    for seq in range(count):
        reading = read_accel()
        if reading is None:
            print(f"[{seq}] citire senzor eșuată, sar peste")
        else:
            x, y, z = reading
            payload = json.dumps(
                {"seq": seq, "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)}
            )
            try:
                # QoS 0 = trimite o dată, fără confirmare de la broker
                client.publish(TOPIC, payload, qos=0).wait_for_publish()
                sent += 1
                print(f"[{seq}] trimis: {payload}")
            except RuntimeError as e:
                print(f"[{seq}] publicare eșuată: {e}")
        time.sleep(INTERVAL_S)

    client.loop_stop()
    client.disconnect()
    print(f"Gata: {sent}/{count} mesaje trimise")


if __name__ == "__main__":
    main()
