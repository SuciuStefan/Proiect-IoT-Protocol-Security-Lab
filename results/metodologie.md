# Metodologie

Scop: compararea MQTT, HTTP și CoAP (RTT, overhead, pierderi) pe aceeași
rețea, cu aceleași date. Toate valorile din raport vin din măsurători
(CSV-uri din `results/`, capturi din `captures/`), nu din estimări.

## 1. Mediu

- Telefon: Samsung S25+, Android 16, Termux 0.118.3, Python 3.14.6
- Laptop: Windows 11, Mosquitto 2.1.2, Python 3.9.13, aiocoap 0.4.7
- Topologie: laptopul e conectat la hotspot-ul telefonului. Telefonul e și
  punct de acces, și client. Nu există router.
- Limitare: traficul nu trece printr-un router separat, deci RTT-ul poate fi
  mai mic și mai variabil decât pe un Wi-Fi obișnuit. Rezultatele sunt
  valabile pentru această topologie.
- Telefon (pachete Python): paho-mqtt 2.1.0, aiocoap 0.4.17, requests 2.34.2
- Laptop: Wireshark 4.6.9 , Npcap 1.88, Node.js v25.2.1, Node-RED v5.0.8
- Hotspot: banda <2.4 SI 5 GHz>
- Condiții: date mobile oprite (dacă hotspot-ul permite), `termux-wake-lock`,
  ecran pornit, aplicații de fundal închise, distanță fixă telefon-laptop
  ~25cm, fără alte dispozitive pe hotspot.
- IP-ul laptopului la măsurători: nu se scrie în repo (variabila `BROKER_HOST`).

## 2. Payload

- JSON identic pe toate protocoalele: `{"seq":N,"x":0.207,"y":-0.077,"z":9.84}`
- Valori de senzor reale (accelerometru), `seq` crește de la 0.
- Dimensiunea payload-ului se măsoară din captură pentru fiecare mesaj
  (variază ușor cu numărul de cifre din seq/valori).
- Topic/cale: MQTT `telefon/accel`, HTTP `POST /accel`, CoAP `POST /accel`.

## 3. Rată și număr de mesaje

- 1 mesaj / secundă, 200 mesaje măsurate per rulare.
- Încălzire: primele 10 mesaje se trimit dar se exclud din statistici.
- 3 rulări per protocol, rezultate raportate separat și agregat.
- Ordinea rulărilor alternată (MQTT, HTTP, CoAP, MQTT, ...) ca derivele
  de rețea să nu favorizeze un protocol.

## 4. Configurația protocoalelor

| Protocol | Transport | Conexiune | Confirmare |
| --- | --- | --- | --- |
| MQTT | TCP 1883 | persistentă, keep-alive 60s | QoS 1 (PUBACK) |
| HTTP | TCP 8000 | persistentă (keep-alive, o sesiune) | răspuns 204 |
| CoAP | UDP 5683 | fără conexiune | CON (Confirmable), ACK |

- QoS 0 și CoAP NON nu au confirmare, deci nu au RTT. Nu se compară.
- Serverul răspunde minimal (204 / 2.04) ca timpul de procesare să fie neglijabil.

## 5. RTT

- Definiție: timpul dintre trimiterea mesajului și primirea confirmării,
  măsurat pe ceasul telefonului cu `time.perf_counter()`.
  - MQTT: publish -> PUBACK
  - HTTP: request -> răspuns complet
  - CoAP: request CON -> ACK/răspuns
- Nu se măsoară latență one-way (ceasurile telefon/laptop nu sunt sincronizate).
- Stabilirea conexiunii (handshake TCP, CONNECT MQTT) se măsoară separat
  și NU intră în RTT-ul pe mesaj.
- Raportat: medie, minim, maxim, mediană, percentila 95, deviație standard.
- RTT include retransmisiile automate (CoAP CON, TCP). Retransmisiile se
  numără din captură (CoAP: același Message ID apare de mai multe ori) și
  se raportează separat.
- Mesaj fără confirmare după 5 s = declarat pierdut, exclus din RTT.

## 6. Overhead

- Sursă: capturi Wireshark pe interfața Wi-Fi a laptopului.
- Filtre: `tcp.port==1883`, `tcp.port==8000`, `udp.port==5683`.
- Se numără de la nivelul IP în sus (header IP + TCP/UDP + protocol + payload),
  fără headerul de nivel legătură.
- Se includ confirmările (PUBACK, răspuns HTTP, ACK CoAP) și ACK-urile TCP
  din regimul stabil. Handshake-ul și keep-alive-urile se raportează separat.
- Se raportează două cifre:
  1. overhead de protocol (doar header MQTT/HTTP/CoAP + confirmare)
  2. overhead pe fir complet (incl. TCP/UDP + IP)
- Formulă: (octeți pe fir per mesaj - octeți payload) / octeți payload.

## 7. Pierderi de pachete

- Mesaje trimise (telefon) vs. mesaje primite (log server, după `seq`).
- Pe LAN/hotspot se așteaptă ~0%. Se raportează valoarea măsurată, fără ajustări.
- Pierderea la nivel de rețea (retransmisii în captură) se raportează separat
  de pierderea la nivel de aplicație (seq lipsă la server). Pe TCP (MQTT/HTTP)
  pierderea la nivel de aplicație e aproape sigur 0 prin construcție.

## 8. Reproductibilitate

- Scripturi: `phone/` (publishere), servere pe laptop. Un script = o responsabilitate.
- Fiecare rulare produce un CSV `results/<protocol>_<rulare>.csv` (seq, timp trimis, RTT).
- Fiecare rulare are o captură `captures/<protocol>_<rulare>.pcap`.

## 9. Amenințări la validitate

- Un singur telefon, un singur laptop, topologie hotspot.
- Eșantion mic (3 x 200 mesaje per protocol).
- Interferențe Wi-Fi necontrolate, economisire de energie pe telefon.
