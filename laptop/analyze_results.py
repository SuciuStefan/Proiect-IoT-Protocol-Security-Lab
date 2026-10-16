"""Calculează tabelele finale (RTT, Overhead, Pierderi) din results/ și captures/.
Respectă strict regulile din results/metodologie.md:
- Exclude primele 10 mesaje de încălzire (seq 0..9) atât din RTT/Pierderi, cât și din Overhead.
- Citește lungimea reală a headerelor IP și TCP (inclusiv opțiunile TCP de 12B) din pachete.
- Raportează separat pachetele de Handshake/Teardown, Keep-Alive și Retransmisiile de rețea.
"""
import csv
import json
import math
import struct
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASE_DIR / "results"
CAPTURES_DIR = BASE_DIR / "captures"

PROTOCOLS = ["mqtt", "http", "coap"]
WARMUP_SEQ = 10  # seq 0..9 sunt încălzire (metodologie secțiunea 3)


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def find_runs(proto):
    runs = []
    for p in sorted(RESULTS_DIR.glob(f"{proto}_*.csv")):
        name = p.stem
        if "_recv_" in name or name.endswith("_test"):
            continue
        runs.append(name.split("_", 1)[1])
    return runs


def analyze_rtt_and_loss():
    rtt_rows = []
    loss_rows = []

    for proto in PROTOCOLS:
        runs = find_runs(proto)
        all_rtts = []
        total_sent = 0
        total_recv = 0

        for run in runs:
            pub_file = RESULTS_DIR / f"{proto}_{run}.csv"
            recv_file = RESULTS_DIR / f"{proto}_recv_{run}.csv"

            run_rtts = []
            sent_seqs = set()

            if pub_file.exists():
                with open(pub_file, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        seq = int(row["seq"])
                        if seq < WARMUP_SEQ:
                            continue
                        sent_seqs.add(seq)
                        val = row["rtt_ms"]
                        if val not in ("LOST", "ERR"):
                            rtt = float(val)
                            run_rtts.append(rtt)
                            all_rtts.append(rtt)

            recv_seqs = set()
            if recv_file.exists():
                with open(recv_file, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        seq = int(row["seq"])
                        if seq >= WARMUP_SEQ:
                            recv_seqs.add(seq)

            if run_rtts:
                s = sorted(run_rtts)
                mean = sum(s) / len(s)
                sd = math.sqrt(sum((x - mean) ** 2 for x in s) / (len(s) - 1)) if len(s) > 1 else 0.0
                rtt_rows.append({
                    "protocol": proto.upper(),
                    "run": run,
                    "n": len(s),
                    "mean": mean,
                    "min": s[0],
                    "max": s[-1],
                    "median": percentile(s, 50),
                    "p95": percentile(s, 95),
                    "std": sd,
                })

            sent_n = len(sent_seqs)
            recv_n = len(sent_seqs.intersection(recv_seqs))
            lost_n = sent_n - recv_n
            total_sent += sent_n
            total_recv += recv_n

            loss_rows.append({
                "protocol": proto.upper(),
                "run": run,
                "sent": sent_n,
                "recv": recv_n,
                "lost": lost_n,
                "loss_pct": (lost_n / sent_n * 100.0) if sent_n > 0 else 0.0,
            })

        if len(runs) > 1 and all_rtts:
            s = sorted(all_rtts)
            mean = sum(s) / len(s)
            sd = math.sqrt(sum((x - mean) ** 2 for x in s) / (len(s) - 1)) if len(s) > 1 else 0.0
            rtt_rows.append({
                "protocol": proto.upper(),
                "run": "AGREGAT",
                "n": len(s),
                "mean": mean,
                "min": s[0],
                "max": s[-1],
                "median": percentile(s, 50),
                "p95": percentile(s, 95),
                "std": sd,
            })
            lost_tot = total_sent - total_recv
            loss_rows.append({
                "protocol": proto.upper(),
                "run": "AGREGAT",
                "sent": total_sent,
                "recv": total_recv,
                "lost": lost_tot,
                "loss_pct": (lost_tot / total_sent * 100.0) if total_sent > 0 else 0.0,
            })

    return rtt_rows, loss_rows


def parse_pcap_steady(pcap_path, proto):
    """Analizează captura .pcap separând regimul stabil (seq >= 10) de încălzire,
    handshake/teardown și keep-alive."""
    with open(pcap_path, "rb") as f:
        data = f.read()

    magic = struct.unpack("<I", data[:4])[0]
    endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
    offset = 24

    pkts = []
    seq_first_idx = {}
    seq_json_len = {}
    idx = 0

    while offset + 16 <= len(data):
        _, _, incl_len, orig_len = struct.unpack(endian + "IIII", data[offset:offset + 16])
        offset += 16
        pkt = data[offset:offset + incl_len]
        offset += incl_len

        if len(pkt) < 34:
            continue

        ip_len = orig_len - 14
        ip_hdr_len = (pkt[14] & 0x0F) * 4
        ip_proto = pkt[23]

        if ip_proto == 6:  # TCP
            tcp_hdr_len = ((pkt[14 + ip_hdr_len + 12] >> 4) & 0x0F) * 4
            l3_l4_len = ip_hdr_len + tcp_hdr_len
            flags = pkt[14 + ip_hdr_len + 13]
        elif ip_proto == 17:  # UDP
            l3_l4_len = ip_hdr_len + 8
            flags = 0
        else:
            l3_l4_len = ip_hdr_len
            flags = 0

        app_len = max(0, ip_len - l3_l4_len)

        seq_found = None
        j_idx = pkt.find(b'{"seq":')
        if j_idx != -1:
            end_idx = pkt.find(b"}", j_idx)
            if end_idx != -1:
                raw_json = pkt[j_idx:end_idx + 1]
                try:
                    obj = json.loads(raw_json.decode("utf-8"))
                    seq_found = int(obj["seq"])
                    if seq_found not in seq_first_idx:
                        seq_first_idx[seq_found] = idx
                        seq_json_len[seq_found] = len(raw_json)
                except Exception:
                    pass

        pkts.append({
            "idx": idx,
            "ip_len": ip_len,
            "l3_l4_len": l3_l4_len,
            "app_len": app_len,
            "flags": flags,
            "seq": seq_found,
            "pkt": pkt,
        })
        idx += 1

    idx_seq0 = seq_first_idx.get(0, 0)
    idx_seq10 = seq_first_idx.get(WARMUP_SEQ, 0)
    if proto == "http":
        # La HTTP, pachetul cu headerele POST este chiar înaintea pachetului cu JSON-ul
        idx_seq0 = max(0, idx_seq0 - 1)
        idx_seq10 = max(0, idx_seq10 - 1)

    fin_idx = len(pkts)
    if proto in ("mqtt", "http"):
        for p in reversed(pkts):
            if p["flags"] & 0x01:  # TCP FIN
                fin_idx = p["idx"]
            elif fin_idx < len(pkts):
                break
        if proto == "mqtt" and fin_idx > 0 and pkts[fin_idx - 1]["app_len"] == 2:
            fin_idx -= 1  # MQTT DISCONNECT

    steady_pkts = pkts[idx_seq10:fin_idx]

    ping_pkts = 0
    ping_ip_bytes = 0
    retrans = 0
    seen_seqs = set()

    for p in steady_pkts:
        if proto == "mqtt" and p["app_len"] == 2:
            mqtt_type = p["pkt"][14 + p["l3_l4_len"]]
            if mqtt_type in (0xC0, 0xD0):  # PINGREQ / PINGRESP
                ping_pkts += 1
                ping_ip_bytes += p["ip_len"]
        if p["seq"] is not None:
            if p["seq"] in seen_seqs:
                retrans += 1
            else:
                seen_seqs.add(p["seq"])

    steady_pkt_count = len(steady_pkts) - ping_pkts
    steady_ip_bytes = sum(p["ip_len"] for p in steady_pkts) - ping_ip_bytes
    steady_app_bytes = sum(p["app_len"] for p in steady_pkts) - (ping_pkts * 2)
    payload_bytes = sum(v for k, v in seq_json_len.items() if k >= WARMUP_SEQ)
    hs_teardown_pkts = idx_seq0 + (len(pkts) - fin_idx)

    return {
        "steady_pkts": steady_pkt_count,
        "payload_B": payload_bytes,
        "app_B": steady_app_bytes,
        "ip_B": steady_ip_bytes,
        "ovh_proto": (steady_app_bytes - payload_bytes) / payload_bytes if payload_bytes else 0.0,
        "ovh_wire": (steady_ip_bytes - payload_bytes) / payload_bytes if payload_bytes else 0.0,
        "retrans": retrans,
        "hs_pkts": hs_teardown_pkts,
        "keepalive_pkts": ping_pkts,
    }


def analyze_overhead():
    rows = []
    for proto in PROTOCOLS:
        for pcap_path in sorted(CAPTURES_DIR.glob(f"{proto}_*.pcap")):
            run = pcap_path.stem.split("_", 1)[1]
            res = parse_pcap_steady(pcap_path, proto)
            if res["payload_B"] > 0:
                rows.append({
                    "protocol": proto.upper(),
                    "run": run,
                    **res,
                })
    return rows


def save_tables(rtt_rows, loss_rows, ovh_rows):
    with open(RESULTS_DIR / "tabel_rtt.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Protocol", "Rulare", "N_masurate", "Medie_ms", "Min_ms", "Max_ms", "Mediana_ms", "P95_ms", "Std_ms"])
        for r in rtt_rows:
            w.writerow([
                r["protocol"], r["run"], r["n"],
                f"{r['mean']:.2f}", f"{r['min']:.2f}", f"{r['max']:.2f}",
                f"{r['median']:.2f}", f"{r['p95']:.2f}", f"{r['std']:.2f}",
            ])

    with open(RESULTS_DIR / "tabel_pierderi.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Protocol", "Rulare", "Trimise_masurate", "Primite_masurate", "Pierdute_aplicatie", "Pierdere_proc"])
        for r in loss_rows:
            w.writerow([r["protocol"], r["run"], r["sent"], r["recv"], r["lost"], f"{r['loss_pct']:.2f}%"])

    with open(RESULTS_DIR / "tabel_overhead.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Protocol", "Rulare", "Pachete_Regim_Stabil", "Octeti_Payload",
            "Octeti_Protocol_L7", "Octeti_IP_Total", "Overhead_Protocol_x",
            "Overhead_Fir_Complet_x", "Retransmisii_Retea", "Pachete_Handshake_Fin", "Pachete_KeepAlive"
        ])
        for r in ovh_rows:
            w.writerow([
                r["protocol"], r["run"], r["steady_pkts"], r["payload_B"],
                r["app_B"], r["ip_B"], f"{r['ovh_proto']:.2f}",
                f"{r['ovh_wire']:.2f}", r["retrans"], r["hs_pkts"], r["keepalive_pkts"]
            ])

    print("Tabele actualizate cu succes în results/!")


if __name__ == "__main__":
    rtt, loss = analyze_rtt_and_loss()
    ovh = analyze_overhead()
    save_tables(rtt, loss, ovh)