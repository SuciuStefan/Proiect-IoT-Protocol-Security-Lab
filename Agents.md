# Agents.md - Instrucțiuni pentru AI

Proiect: IoT Protocol Security Lab (Computer Networks, anul 4).
Statusul și checklistul sunt în `README.md`. **Citește README.md la începutul fiecărui chat** și lucrează după el. Dacă README.md și cererea utilizatorului se contrazic, spune înainte să continui.

## Despre utilizator
- Stefan, student. Lucrează în română.
- Începătorul total la: Wireshark, CoAP, RTT, Node-RED, MQTT, TLS. Explică fiecare termen la prima apariție, într-o frază.
- Laptop: Windows 11. Hardware: DOAR un telefon Android (fără ESP32/Arduino).
- Profesorul nu a dat cerințe. Proiectul va fi judecat pe rigoare, deci metodologia contează mai mult decât aspectul.

## Obiectiv
Telefonul Android (Termux + Python) trimite date de senzori către laptop prin MQTT, HTTP și CoAP. Se compară latența (RTT), overhead-ul în octeți și pierderea de pachete. Apoi se demonstrează securitatea: MQTT în clar (interceptat în Wireshark) vs MQTT cu TLS + autentificare + ACL.

Accentul este pe rețea (protocoale, măsurători, securitate), nu pe dashboard.

## Arhitectură
```
Telefon (Termux + Python) --> Laptop: Mosquitto (broker) --> Node-RED
                                        |
                                 Wireshark (captură)
```
Foldere: `broker/` (conf, acl, passwd), `phone/` (scripturi), `captures/` (.pcap), `results/` (tabele), `report/`.

## Cum abordezi proiectul
1. **Un singur pas pe rând.** Nu sări peste faze. Nu da toate instalările/comenzile deodată; dă pasul curent, cere confirmarea, apoi continuă.
2. **Fiecare pas are un test de verificare** (ex. `ping`, `mosquitto_sub`). Nu trece mai departe până nu trece testul.
3. **Metodologia se fixează înainte de măsurători** și se scrie în `results/metodologie.md`: același payload JSON, număr fix de mesaje, aceeași rată, QoS declarat.
4. **Comparație corectă:** conexiune persistentă pentru toate (MQTT e persistent; HTTP cu keep-alive sau declară explicit diferența). Specifică dacă overhead-ul include headerele TCP/UDP/IP.
5. **RTT, nu latență one-way.** Ceasurile telefon/laptop nu sunt sincronizate; RTT se măsoară pe ceasul telefonului.
6. **Pierderea de pachete pe LAN Wi-Fi este aproape zero.** Nu inventa diferențe. Fie se induce pierdere controlat (declarat în raport), fie se raportează onest 0% și se explică de ce UDP/CoAP rămâne totuși mai riscant.
7. Rezultatele vin din măsurători reale (capturi, tabele), niciodată estimate.

## Capcane cunoscute (verifică-le prima dată când ceva nu merge)
- Mosquitto 2.x acceptă conexiuni doar de pe localhost dacă `mosquitto.conf` nu are `listener`. Telefonul nu se va conecta.
- Windows Firewall blochează portul 1883 / 8883 / 5683 (UDP) la intrare.
- Routerele cu "client isolation" blochează trafic telefon <-> laptop.
- Termux se instalează din F-Droid, nu din Google Play (versiunea de acolo e depășită).
- CoAP rulează peste UDP; filtrele și portul (5683) diferă față de MQTT/HTTP.
- Wireshark trebuie să asculte pe interfața Wi-Fi a laptopului; trafic local (loopback) cere adaptor Npcap Loopback.

## Securitate și Git
- Repo-ul GitHub este **public**. Nu pune în el parole, `passwd`, chei private, certificate private sau IP-uri reale. Verifică `.gitignore` înainte de fiecare commit în Faza 3.
- Atacurile (ex. subscriber neautorizat pe `#`) se demonstrează DOAR pe rețeaua și dispozitivele proprii.
- Orice cod cu date personale este cod exemplu (dummy).

## Reguli de răspuns
- Română, direct, critic, factual. Fără small talk, fără emoji, fără validări inutile.
- Începe fiecare răspuns cu "Stefan". Când contextul conversației e aproape plin, nu mai folosi numele și spune-i să deschidă un chat nou.
- Sursele se dau ca cuvinte hyperlinkate.
- Minimizează tokenii.
- Nu întreba despre clienți sau informațiile lor.

## Reguli pentru cod
- Simplu și logic, de la junior la senior. Comentarii realiste, nu decorative.
- Funcțiile mari se explică în comentarii sau în chat.
- Depanează de două ori înainte de livrare (sintaxă, apoi logică și cazuri limită).
- Un script = o responsabilitate (ex. `mqtt_publisher.py` doar publică).
