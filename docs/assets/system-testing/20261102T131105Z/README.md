# Dokazi vzdržljivostnega testa, 2. 11. 2026

Ponovitev `20261102T131105Z`: veljavno trajanje in populacija; FAIL zaradi časovnih kriterijev. Vzorci ciljne faze so ločeni od celotnega zagona. Prvi prekinjeni zagon in pilot se ne prištevata ponovitvi.

- `manifest.json`, `profile.json`: različice in dejanske nastavitve zagona.
- `summary.json`: samodejna ocena in petminutni intervali, iz nespremenjenih dogodkov.
- `metrics.json`: točni percentili, statistike vseh/ciljnih zahtev, urni pregled, infrastruktura in pokritje populacije.
- `odzivni-casi.png`, `infrastruktura.png`: grafi iz izvornih dogodkov in meritev.
- `SHA256SUMS-run.txt`: SHA-256 datotek izvorne mape veljavnega zagona (relativne poti glede na `retry/run` v arhivu).
- `state.json`, `verify-restore.log`, `server-postcheck.txt`: dokaz zaključka in obnove staginga.
- `cleanup.log`: odstranitev naših sintetičnih profilov; prvotnih uporabnikov ostane 29.

Celotni arhiv za prilogo oddaji: **NIDiKo-dokazi-2026-11-02.zip** (5,470,961 bajtov). Hrani ga avtor zunaj zgodovine Git; ni samodejno objavljen ali naložen na GitHub. Izbrani dokazi v tej mapi so namenjeni pregledu poročila tudi brez arhiva.

SHA-256 arhiva:

```text
4b4819282cab71b81ccb176409a929d8ac00178e065e0627bb845928f26eb0ec
```

V arhivu: `retry/run` in `retry/generator.jsonl`, ločena prekinjena izvedba, pilot, dnevniki obnove/čiščenja in testna koda. Zasebne evidence uporabniških profilov, poverilnice in podpisani URL-ji so izključeni.

Ponovna analiza brez prometa proti stagingu:

```text
python test-source/scripts/analyze_results.py retry/run
python test-source/scripts/finalize_evidence.py --run retry/run --generator retry/generator.jsonl --output ponovno-generirani-dokazi
```

Za grafe namesti `test-source/report-requirements.txt`. Prvi ukaz zaradi izmerjenega FAIL vrne izhodno kodo 1; to ni napaka obdelave. Izvorni podatki ostanejo nespremenjeni, izpeljana summary/HTML pa se lahko ponovno ustvarita. Brez surovih dogodkov ni mogoče iz teh izbranih povzetkov rekonstruirati vseh zahtev.
