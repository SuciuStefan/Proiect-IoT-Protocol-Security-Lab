# COMENZI.md - comenzi de rulat (laptop Windows 11 + telefon Termux)

Referință rapidă pentru Faza 0-1. Se completează pe parcurs (Faza 2-3 adaugă comenzi noi).
Nu pune aici IP-uri reale, parole sau chei: repo-ul e public. `<IP_laptop>` = valoarea din `ipconfig`.

## Setare o dată per fereastră CMD

Calea proiectului are spații, deci se pune între ghilimele peste tot. Setezi o variabilă (în fiecare CMD nou):

```
set PROIECT=C:\Users\stefa\Desktop\Facultate\Anul 4\SEM1\CN\IoT-Security
```

## LAPTOP

### CMD 1 - Administrator (broker). Rămâne deschis cât ții testele

Deschidere: Start > scrie `cmd` > clic dreapta > "Run as administrator".

**O singură dată** (rularea repetată nu strică):

```
net stop mosquitto
netsh advfirewall firewall add rule name="Mosquitto 1883" dir=in action=allow protocol=TCP localport=1883 profile=private
```

- `net stop mosquitto`: oprește serviciul Windows care ocupă portul 1883 (altfel: `Only one usage of each socket address`). Se refă și după fiecare repornire a laptopului, dacă serviciul pornește singur.
- Regula de firewall se aplică doar rețelelor "Private". Verificare: `netsh advfirewall firewall show rule name="Mosquitto 1883"`.

**De fiecare dată** (pornire broker cu config-ul proiectului):

```
cd "C:\Program Files\mosquitto"
mosquitto -v -c "%PROIECT%\broker\mosquitto.conf"
```

Corect: `Opening ipv4 listener on port 1883` și `mosquitto version ... running`, fără `local only mode`.
Oprire: Ctrl+C. Închiderea ferestrei oprește broker-ul (telefonul primește `connection was lost`).

### CMD 2 - normal (abonat, vede ce trimite telefonul)

```
cd "C:\Program Files\mosquitto"
mosquitto_sub -h localhost -t telefon/accel
```

### CMD 3 - normal (opțional, test de publicare de pe laptop)

```
cd "C:\Program Files\mosquitto"
mosquitto_pub -h localhost -t test -m "salut"
```

### Aflarea IP-ului laptopului (normal)

```
ipconfig
```

Cauți "IPv4 Address" la adaptorul Wi-Fi (`192.168.x.x`). Se poate schimba între sesiuni.

## TELEFON (Termux)

**O singură dată:**

```
pkg update
pkg install python mosquitto termux-api
pip install paho-mqtt
```

Scriptul `mqtt_publisher.py` se copiază în `~` (folderul Termux).

**Test senzor** (numele parțial evită confuzia O/0):

```
termux-sensor -s "Accelerometer Non-wakeup" -n 1
```

Corect: JSON cu `values` (x, y, z). `No valid sensors were registered!` = nume greșit.

**Publicare spre laptop** (broker + abonat pornite pe laptop, același Wi-Fi):

```
cd ~
python mqtt_publisher.py <IP_laptop> 10
```

Corect: `[0] trimis: {...}` până la `[9]`, apoi `Gata: 10/10 mesaje trimise`.

**Test complet doar pe telefon** (fără laptop):

```
cd ~
mosquitto > /dev/null 2>&1 &
sleep 1
mosquitto_sub -t telefon/accel -C 5 &
python mqtt_publisher.py 127.0.0.1 5
pkill mosquitto
```

**Oprirea unei comenzi blocate:** Volum jos + C (sau tasta CTRL din bara de sus, apoi C).

## Depanare rapidă

| Simptom | Cauză probabilă |
| --- | --- |
| `Only one usage of each socket address` | serviciul Windows rulează încă: `net stop mosquitto` (CMD admin) |
| `Unable to open config file` | cale greșită sau fișier salvat ca `mosquitto.conf.txt`; verifică `%PROIECT%` și `dir` |
| `local only mode` în log | broker pornit fără `-c ...mosquitto.conf` |
| Telefonul se blochează / `Connection refused` | broker oprit, IP greșit, Wi-Fi "Public", firewall sau client isolation în router |
| `connection was lost` pe telefon | fereastra broker-ului a fost închisă |
| `No valid sensors were registered!` | nume senzor greșit; folosește `"Accelerometer Non-wakeup"` |
