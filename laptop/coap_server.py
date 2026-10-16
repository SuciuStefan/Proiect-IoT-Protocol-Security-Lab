"""Server CoAP minimal pentru măsurători.
Singura sarcină: primește POST /accel, notează seq și răspunde 2.04 Changed."""
import asyncio
import json
import socket
import sys
from pathlib import Path
from aiocoap import Context, Message, Code, resource

PORT = 5683
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

received = []  # seq-urile primite, în ordinea sosirii (pentru calculul pierderilor)


def get_bind_ips():
    """Returnează lista de IP-uri locale pe care poate asculta serverul.
    Pe Windows, aiocoap (simplesocketserver) interzice '0.0.0.0' și '',
    deci trebuie legat explicit pe fiecare IP local (127.0.0.1 + Wi-Fi).
    """
    ips = {"127.0.0.1"}
    try:
        _, _, host_ips = socket.gethostbyname_ex(socket.gethostname())
        for ip in host_ips:
            if not ip.startswith("169.254."):
                ips.add(ip)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass

    return sorted(ips)


class AccelResource(resource.Resource):
    """Resursa care primește POST /accel."""

    async def render_post(self, request):
        try:
            payload = request.payload.decode("utf-8")
            data = json.loads(payload)
            seq = int(data["seq"])
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            return Message(code=Code.BAD_REQUEST)

        received.append(seq)
        # 2.04 Changed este echivalentul CoAP pentru HTTP 204 No Content
        return Message(code=Code.CHANGED)


async def amain():
    root = resource.Site()
    root.add_resource(["accel"], AccelResource())

    contexts = []
    for ip in get_bind_ips():
        try:
            ctx = await Context.create_server_context(root, bind=(ip, PORT))
            contexts.append(ctx)
            print(f"Ascult CoAP pe UDP {ip}:{PORT}")
        except OSError as e:
            print(f"Avertisment: nu am putut lega {ip}:{PORT} ({e})")

    if not contexts:
        raise RuntimeError("Nu s-a putut porni serverul pe nicio interfață.")

    print("Server pornit. Apasă Ctrl+C pentru oprire.")
    try:
        while True:
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    finally:
        for ctx in contexts:
            await ctx.shutdown()


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else "test"

    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass
    finally:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / f"coap_recv_{run}.csv"
        with open(path, "w", encoding="utf-8") as f:
            f.write("seq\n")
            for s in received:
                f.write(f"{s}\n")
        print(f"{len(received)} mesaje primite, salvate în {path}")


if __name__ == "__main__":
    main()