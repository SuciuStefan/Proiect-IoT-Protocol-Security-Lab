# Proiect IoT - Protocol Security Lab

Computer Networks, anul 4. Telefon Android ca nod IoT: comparație MQTT / HTTP / CoAP (RTT, overhead, pierderi) + demonstrație de securitate (MQTT în clar vs TLS + autentificare + ACL).

Detalii despre temă, unelte și reguli: vezi `Agents.md`.
**Acest fișier este sursa de adevăr pentru status.** Bifezi `[x]` pe măsură ce termini un pas.

## Status curent

**Faza activă:** 2 - Mediu
**Ultimul pas terminat:** Windows 11 confirmat pe laptop

## Arhitectură

```text
Telefon (Termux + Python) --> Laptop: Mosquitto (broker) --> Node-RED (vizualizare)
                                        |
                                 Wireshark (captură)
```

## Checklist

### Faza 0 - Mediu

- [x] Sistem de operare laptop: Windows 11
- [x] Laptop: Mosquitto instalat
- [x] Laptop: Wireshark instalat (cu Npcap)
- [x] Laptop: Node.js + Node-RED instalate
- [x] Telefon: Termux + Termux:API (din F-Droid)
- [x] Telefon: `pkg install python` în Termux
- [x] Telefon și laptop în același Wi-Fi
- [x] `ping` telefon -> laptop reușit (dacă pică: "client isolation" în router)
- [x] Windows Firewall: regulă de intrare pentru portul 1883

### Faza 1 - Prototip fără securitate

- [x] `broker/mosquitto.conf` cu listener pe 1883 și `allow_anonymous true` (DOAR pentru test)
- [x] Test local: `mosquitto_pub` / `mosquitto_sub` pe laptop
- [x] Test de pe telefon spre laptop (publish din Termux)
- [x] `phone/mqtt_publisher.py` citește un senzor (`termux-sensor`) și publică
- [x] Node-RED primește din MQTT și afișează valorile
- [x] Commit în Git

### Faza 2 - HTTP, CoAP, măsurători

- [x] Metodologie fixată în `results/metodologie.md` (payload JSON, număr mesaje, rată, QoS)
- [x] Server HTTP pe laptop
- [x] Server CoAP pe laptop (ex. aiocoap)
- [x] `phone/http_publisher.py`
- [x] `phone/coap_publisher.py`
- [x] Captură Wireshark MQTT -> `captures/`
- [x] Captură Wireshark HTTP -> `captures/`
- [x] Captură Wireshark CoAP -> `captures/`
- [x] Tabel RTT (medie, min, max) per protocol -> `results/`
- [x] Tabel overhead (octeți pe fir / octeți payload) per protocol -> `results/`
- [x] Tabel pierderi de pachete per protocol -> `results/`

### Faza 3 - Securitate

- [ ] Captură MQTT în clar: date vizibile în Wireshark (dovadă)
- [ ] Certificate generate (CA + server TLS)
- [ ] Mosquitto cu TLS pe 8883
- [ ] Autentificare: `allow_anonymous false` + fișier `passwd`
- [ ] ACL: telefonul poate doar publica pe topicul lui
- [ ] Captură MQTT cu TLS: conținut ilizibil (dovadă)
- [ ] Atac pe rețeaua proprie: subscriber neautorizat pe `#` reușește fără ACL
- [ ] Același atac eșuează cu autentificare + ACL
- [ ] Verificat: `passwd`, `*.key`, parole reale NU sunt în Git (`.gitignore`)

### Faza 4 - Documentație și demo

- [ ] Raport în `report/` (metodologie, tabele, capturi, concluzii)
- [ ] Grafice din `results/`
- [ ] Demo repetată cap-coadă cel puțin o dată
- [ ] Prezentare / pregătire pentru profesor

## Jurnal

| Data       | Ce s-a făcut |
|------------|--------------|
| 2026-10-09 | Plan stabilit, repo creat, Windows 11 confirmat |
| 2026-10-14 | Telefon -> Mosquitto -> Node-RED funcțional, flow exportat, commit Faza 1 |

## Structura folderului

```text
iot-securitate/
├── broker/     # mosquitto.conf, acl, passwd (passwd NU în Git)
├── phone/      # scripturi Termux (publisher MQTT/HTTP/CoAP)
├── captures/   # fișiere .pcap (dovezi)
├── results/    # tabele latență, overhead, pierderi
└── report/     # documentația finală
```

## Reguli

- Atacurile se demonstrează DOAR pe rețeaua și dispozitivele proprii.
- Toate datele din cod și capturi sunt de test (dummy).
