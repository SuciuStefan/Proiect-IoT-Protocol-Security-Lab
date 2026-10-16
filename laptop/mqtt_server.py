"""Abonat MQTT minimal pentru măsurători.
Singura sarcină: ascultă telefon/accel (QoS 1), notează seq și salvează la oprire."""
import json
import sys
from pathlib import Path
import paho.mqtt.client as mqtt

BROKER_HOST = "127.0.0.1"
PORT = 1883
TOPIC = "telefon/accel"

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
received = []  # seq-urile primite, în ordinea sosirii (pentru calculul pierderilor)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(TOPIC, qos=1)
        print(f"Conectat la broker {BROKER_HOST}:{PORT}, abonat la '{TOPIC}'. Ctrl+C pentru oprire.")
    else:
        print(f"Eroare la conectare: {reason_code}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        received.append(int(data["seq"]))
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        pass


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else "test"

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_HOST, PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    except OSError as e:
        sys.exit(f"Nu mă pot conecta la broker ({BROKER_HOST}:{PORT}) - {e}")
    finally:
        client.disconnect()
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / f"mqtt_recv_{run}.csv"
        with open(path, "w", encoding="utf-8") as f:
            f.write("seq\n")
            for s in received:
                f.write(f"{s}\n")
        print(f"{len(received)} mesaje primite, salvate în {path}")


if __name__ == "__main__":
    main()