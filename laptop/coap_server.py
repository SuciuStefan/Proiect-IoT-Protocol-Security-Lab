"""Server CoAP minimal pentru măsurători.
Singura sarcină: primește POST /accel, notează seq și răspunde 2.04 Changed."""
import json
import os
import sys
import asyncio
from aiocoap import resource, Message, Code
from aiocoap import Context


received = []  # seq-urile primite, în ordinea sosirii (pentru calculul pierderilor)


class AccelResource(resource.Resource):
    """Resursa care primește POST /accel."""

    async def render_post(self, request):
        try:
            # Corpul mesajului conține JSON cu seq
            payload = request.payload.decode('utf-8')
            data = json.loads(payload)
            seq = data["seq"]
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            # Raspuns 4.00 Bad Request
            return Message(code=Code.BAD_REQUEST)

        received.append(seq)
        # Raspuns 2.04 Changed (echivalentul HTTP 204 No Content)
        return Message(code=Code.CHANGED)


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else "test"  # numărul rulării

    async def amain():
        # Creăm arborescuta de resurse
        root = resource.Site()
        root.add_resource(['accel'], AccelResource())

        # Creăm contextul de server
        # NOTA: pe Windows, aiocoap nu acceptă '0.0.0.0', folosim '' în loc
        await Context.create_server_context(root, bind=('', 5683))
        print(f"Ascult pe 0.0.0.0:5683. Ctrl+C pentru oprire.")

        # Rulează până la întrerupere
        try:
            await asyncio.get_running_loop().create_future()  # rulează pentru totdeauna
        except KeyboardInterrupt:
            pass

    # Rulează bucla de evenimente
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass
    finally:
        # Salvăm la oprire, nu la fiecare mesaj
        os.makedirs("results", exist_ok=True)
        path = f"results/coap_recv_{run}.csv"
        with open(path, "w") as f:
            f.write("seq\n")
            for s in received:
                f.write(f"{s}\n")
        print(f"{len(received)} mesaje primite, salvate în {path}")


if __name__ == "__main__":
    main()