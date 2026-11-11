# Avtomatizirani funkcionalni testi

Selenium s headless Chromom izvede šest scenarijev in 23 korakov iz
[prejšnje naloge](../../../docs/16-porocilo-funkcionalno-testiranje.md).
[Kratko poročilo in arhitektura CI](../../../docs/20-avtomatizirano-funkcionalno-testiranje-ci.md).

## Ponovljiv lokalni zagon

Potrebujemo Python 3.12 ali 3.13, Node.js 24, npm, Docker in Chrome. Selenium Manager
poišče Chrome in ustrezni ChromeDriver ter manjkajoče komponente prenese; prvi zagon
zato potrebuje dostop do spleta. Na minimalnem Linuxu so potrebne tudi sistemske
knjižnice Chroma, npr. `libnss3` in `libasound2t64` na Ubuntu 24.04.

Ukazi iz korena repozitorija (PowerShell):

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
docker run --detach --rm --name nidiko-functional-mongo --publish 127.0.0.1:27028:27017 mongo:7.0
python backend/tests/functional/run_local_suite.py --output-dir test-results/local-01
docker stop nidiko-functional-mongo
```

Na Linuxu virtualno okolje aktiviramo z `source backend/.venv/bin/activate`.
Vsak ponoven zagon zahteva novo izhodno mapo, npr. `test-results/local-02`.
Testni MongoDB mora biti zagnan; suite ustvari novo bazo `nidiko_functional_<id>` in
nikoli ne briše ali prepisuje obstoječih baz. Uvoz sprejme le loopback MongoDB URI in
novo, prazno bazo z navedeno predpono. Kontejner nima volumna; `docker stop` skupaj z
`--rm` odstrani vse njegove začasne podatke.

Suite sam zgradi in zažene pravi frontend na `http://localhost:5173`, pravi FastAPI
na `http://localhost:8008` in omejen nadomestek Supabase na `http://localhost:54321`.
Ta vrata morajo biti prosta. Uporabniškega `.env` ne spreminja; testne vrednosti posreduje
samo podprocesom. Podatke uvozi iz `backend/data/nova_verzija_data` in iz mape `fixtures`.

Izvede osnovni nabor, začasno spremeni naslov domače strani v `frontend/index.html` in
`frontend/src/app/PageTitleManager.tsx`, ponovno zgradi aplikacijo ter ponovi TS-01.
Zahteva točno en neuspeh v koraku 1.1 in izhodno kodo 1. V `finally` obnovi obe izvorni
datoteki in zgradi zdravo aplikacijo, nato zahteva ponovni PASS scenarija TS-01.
Napaka namestitve/brskalnika ali nepovezan neuspeh ne štejeta kot zaznana mutacija.
Celoten suite vrne 0 samo za zaporedje izhodov **0 → 1 → 0** in ustrezne zapisnike.
Suite začasno spreminja navedeni izvorni datoteki; med njegovim izvajanjem ju ne urejamo.

## Rezultati

- `baseline/`: vseh šest scenarijev pred mutacijo.
- `intentional-defect/`: TS-01 z namerno napako.
- `restored/`: TS-01 po obnovi.
- Vsaka mapa vsebuje `test_execution_summary.json`, `junit.xml` in posnetke PNG.
- Ob neuspehu so dodani HTML in dnevnik brskalnika; izvirna napaka ostane tudi ob
  neuspešnem zajemu diagnostike.
- V korenu so dnevniki gradnje in storitev, patch namerne napake ter `mutation_summary.json`.
- Pri napaki celotnega suite nastane `suite_error.txt`; izhod je 1.

CI objavi artefakt `selenium-functional-test-results` in GitHub Step Summary tudi ob
neuspehu. Artefakti se hranijo 14 dni. V repozitoriju so izbrani trajni dokazi v `docs/assets`.

## Preverjanje pravega staginga

```powershell
python backend/tests/functional/run_functional_tests.py --base-url http://46.225.17.135 --output-dir test-results/staging-01
```

Enakovreden ročni GitHub workflow je **Staging functional tests (external services)**.
Tu ni nadomestka Supabase: storitev, konfiguracija in podatki morajo res delovati.
Preverjanje napačne prijave ostane strogo; splošna omrežna napaka ne pomeni PASS.
Po potrebi izberemo scenarije z `--scenarios 1 4 6`; neizbrani scenariji niso označeni kot uspešni.
Ne uporabljamo `python -O`, ker izklopi `assert`; poganjalnik tak zagon zavrne.

## Regresijski testi poganjalnika brez brskalnika

```powershell
python -m pytest backend/tests/functional/test_runner_regressions.py --confcutdir=backend/tests/functional -q
```

## Dodatni kontrolirani test prijavnega vmesnika

Ohranjen je tudi `run_auth_ui_test.py` iz commita `f231b2b`. CI ga izvede nad
lokalnim frontendom na vratih 5179 z nadzorovanim odgovorom `invalid_credentials`.
Preverja prijavni vmesnik brez pravega Supabase. Starejši dokaz mutacije prevoda
je v `docs/20-avtomatizirano-funkcionalno-testiranje.md`; nov celotni nabor in
dokaz mutacije naslova sta opisana v poročilu s pripono `-ci.md`.
