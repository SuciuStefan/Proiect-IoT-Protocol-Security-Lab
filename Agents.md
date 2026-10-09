# Proiect IoT - Computer Networks (anul 4)

## Context
- Materie: Computer Networks, anul 4. Profesorul nu a dat cerințe detaliate.
- Student: Stefan. Limba de lucru: română.
- Hardware: DOAR un telefon Android. Fără ESP32/Arduino.
- Obiectiv: proiect cu accent pe partea de rețea (protocoale, măsurători, securitate), nu un simplu dashboard cu senzori.

## Tema aleasă
**IoT cu telefon ca nod + comparație de protocoale + securitate.**

1. Telefonul Android trimite date de senzori (accelerometru, lumină, GPS).
2. Aceleași date sunt trimise prin MQTT, HTTP și CoAP.
3. Se compară: latență, overhead în octeți, pierdere de pachete.
4. Se demonstrează securitatea: MQTT în clar (interceptat în Wireshark) vs MQTT cu TLS + autentificare + ACL.

## Arhitectură planificată
```
Telefon (Termux + Python)  -->  Laptop: Mosquitto (broker)  -->  Node-RED (vizualizare)
                                         |
                                  Wireshark (captură trafic)
```

## Unelte
- Telefon: Termux + Python (sau o aplicație de tip Sensor Server)
- Broker: Mosquitto
- Vizualizare: Node-RED
- Analiză trafic: Wireshark
- Protocoale: MQTT, HTTP, CoAP

## Structura folderului
```
iot-securitate/
├── broker/     # mosquitto.conf, acl, passwd
├── phone/      # scripturi Termux (publisher MQTT/HTTP/CoAP)
├── captures/   # fișiere .pcap (dovezi)
├── results/    # tabele latență, overhead, pierderi
└── report/     # documentația finală
```

## Faze
1. Prototip funcțional: telefon -> Mosquitto -> Node-RED (fără securitate).
2. Adăugare HTTP și CoAP, măsurători în Wireshark.
3. Securitate: TLS, autentificare, ACL, demonstrație de atac (subscriber neautorizat pe `#`).
4. Documentație și demonstrație.

## Status curent
- [ ] Faza 1
- [ ] Faza 2
- [ ] Faza 3
- [ ] Faza 4

Sistem de operare laptop: _(de completat)_

## Reguli pentru asistent
- Răspunde în română, direct, critic și factual. Fără small talk, fără emoji, fără validări inutile.
- Sursele se dau ca cuvinte hyperlinkate.
- Codul: simplu, comentat realist, logic pentru junior și senior. Depanează-l de două ori înainte de livrare.
- Orice cod cu date personale este cod exemplu (dummy).
- Atacurile se demonstrează DOAR pe rețeaua și dispozitivele proprii.
- Minimizează tokenii.
- Nu întreba despre clienți sau informațiile lor.
