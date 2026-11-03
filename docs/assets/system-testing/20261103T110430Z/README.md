# Dokazi večstopenjskega stresnega testa, 3. 11. 2026

Izvedba stresnega testa `20261103T110430Z` (drugi član ekipe): celoten večstopenjski cikel z ogrevanjem (20 mest), sedmimi stopnjami naraščajoče obremenitve (20 do 220 mest), okrevanjem (20 mest) in ohladitvijo (0 mest).

- `manifest.json`: meta podatki zagona, časovni žigi, izvedeni ukazi in hash profila.
- `profile.json`: profil večstopenjske obremenitve (trajanje faz, koraki, stopnja dodajanja, SLA pragovi in varnostna pravila zgodnje ustavitve).
- `summary.json`: natančne metrike po posameznih stopnjah (število zahtev, RPS, delež napak, p95, p99, max latence po skupinah zahtev ter primerjava okrevanja).
- `report.html`: samostojno HTML poročilo z interaktivnimi preglednicami in vdelanimi SVG grafi napredovanja odzivnih časov in prepustnosti.
- `cleanup.log`: dnevnik preverjanja in čiščenja testnih podatkov v MongoDB po zaključku testiranja.
- `SHA256SUMS-run.txt`: SHA-256 kontrolne vsote priloženih dokaznih datotek.

Izvirni dogodki (`events.jsonl`), podrobni zgodovinski izpisi Locusta (`locust_stats_history.csv`) ter celotni dnevniki zagona (`run.log`) se hranijo v mapi rezultatov `test-results/performance/stress/20261103T110430Z/`.
