# Avtomatizirano funkcionalno testiranje in vključitev v CI/CD

**Datum:** 11. 11. 2026. **Projekt:** NIDiKo (React/TypeScript, FastAPI/Python, MongoDB).
**Podlaga:** commit `873ca8933ca3f9848c043beb2a4396508a0a814e` in šest scenarijev iz
[prejšnje naloge](16-porocilo-funkcionalno-testiranje.md). Spodnji rezultati pripadajo
lokalnemu zagonu popravkov; niso rezultat novega GitHub Actions zagona.

## Izbira in namestitev orodja

Izbrali smo **Selenium WebDriver za Python**. Omogoča preverjanje uporabniških tokov
v dejanskem brskalniku ne glede na jezik frontenda, uporablja isti jezik kot zaledje
in ohrani avtomatizacijo vseh šestih obstoječih scenarijev. Različica je pripeta na
`4.52.0` v `backend/tests/functional/requirements.txt`; namestitev je vključena v
`python -m pip install -r backend/requirements.txt`.

Chrome se zažene z `--headless=new`, zato grafično okolje in Xvfb nista potrebna.
Potrebuje Python, Chrome, združljiv ChromeDriver, sistemske knjižnice brskalnika in
zagnano aplikacijo. [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/)
poišče ali prenese ustrezen brskalnik in gonilnik. CI pripravo izvede izrecno in
njuni poti posreduje poganjalniku. Začetno prenašanje odvisnosti zahteva omrežje.

Za ponovljiv funkcionalni zagon so dodatno potrebni Node.js 24 za gradnjo frontenda,
MongoDB 7.0 z lastnimi podatki in omejen lokalni nadomestek Supabase Auth. Slednji
vrne pravilno protokolarno zavrnitev samo za dokumentirane napačne prijavne podatke;
ne izda seje. Preverimo tudi, da je aplikacija res poslala natanko eno tako zahtevo.
Testi preverjajo prijavni UI in obravnavo odgovora; **ne dokazujejo delovanja pravega
Supabase, registracije ali uspešne prijave**. AI scenarij preveri vnos osnutka in
omogočen gumb; vprašanja ne pošlje zunanji AI storitvi.

## Cevovod in podatki

`.github/workflows/functional-tests.yml` je skupni workflow za CI ob PR/pushu in za
preverjanja pred namestitvijo na staging:

1. Checkout revizije, namestitev odvisnosti in priprava Chroma/gonilnika.
2. Zagon ločene MongoDB storitve z zdravstvenim preverjanjem.
3. Uvoz v novo bazo `nidiko_functional_<id>`; sestava in zagon pravega frontenda ter API.
4. Preverjanje pripravljenosti procesov in HTTP končnih točk; ob izteku se zagon prekine.
5. Vseh šest scenarijev, vnos namerne napake, preverjanje zaznave, obnova in ponovitev.
6. Izvoz GitHub Step Summary in artefakta tudi ob neuspehu; hramba 14 dni.

Testi ne potrebujejo GitHub skrivnosti, pravega uporabniškega računa ali staging baze,
zato jih lahko izvajajo tudi PR iz razvejanih repozitorijev. Uvoz dovoli le loopback
MongoDB URI in prazno bazo z zahtevano predpono. Podatke prebere iz
`backend/data/nova_verzija_data`, ki vsebuje trenutno shemo `steps`. V tej zbirki ni
`mod_014` in `ue_036` iz prejšnjih scenarijev, zato so ustrezni javni učni podatki
zamrznjeni v [fixtures](../backend/tests/functional/fixtures/README.md). Med CI se ne
prenašajo s staginga. Vsak scenarij dobi nov zavihek in očiščeno shrambo ter piškotke.

Namestitev na staging zahteva uspeh običajnih preverjanj in funkcionalnega workflowa.
Po namestitvi ločeno preverjanje zahteva pravi HTML naslov ter odgovor API z učnimi
podatki `up_001`. Čakanje ima omejene čase zahtev in ob izteku vrne neuspeh. Staging
opravila se medsebojno ne prekinejo sredi namestitve (`cancel-in-progress: false`).
Ročni workflow **Staging functional tests (external services)** še vedno izvede vseh
šest scenarijev nad objavljeno aplikacijo in pravim Supabase. Njegovi rezultati so
ločeni od izoliranih CI rezultatov. Obstoječa preverjanja prijave niso sproščena na
sprejem splošne omrežne napake.

Izhodi so **JSON**, **JUnit XML**, posnetki **PNG**, ob neuspehu še HTML in dnevnik
brskalnika ter dnevniki storitev. Izhodna koda neposrednega poganjalnika je 0 samo,
če je vsak pričakovani korak izbranih scenarijev izveden natanko enkrat in uspešen.
Manjkajoč zapisnik, podvojen korak, napaka brskalnika ali poljuben FAIL preprečijo uspeh.
Obstoječe mape dokazov se ne prepisujejo. Zagon s `python -O` je zavrnjen.

## Kaj je bilo popravljeno

V [navedenem GitHub zagonu](https://github.com/McTehno/NIDiKo/actions/runs/41881074832)
so bila opravila CI in deploy uspešna, korak Selenium pa se je končal z izhodom 1.
Javni API to potrdi; podrobni dnevnik tega zagona zahteva avtentikacijo. Zato ne
pripisujemo vseh napak starega zagona enemu nepotrjenemu vzroku.

Odpravljeni so globalno deljeni URL/izhodi med instancami poganjalnika, pavšalna
časovna čakanja, možnost uporabe starega naslova med React navigacijo, stale elementi,
šibka preverjanja naslednjega vprašanja in samoocene ter napačno štetje podvojenih
korakov. Iskanje preveri tudi neobstoječ niz, da prikaz začetnih kartic sam po sebi
ne zadostuje za uspeh. Samoocena zahteva shranjen rezultat, ne zgolj naslova sekcije,
ki je viden tudi pred oddajo. Mobilni dokaz je zajet pred odstranitvijo emulacije.
Dodana sta JUnit izvoz in diagnostika napak; odpoved zajema ne prekrije prvotne napake.

Pri neodvisnem preverjanju 11. 11. 2026 je Supabase gostitelj iz javno objavljene
aplikacije `slkxdrljuhxmesrhwsoc.supabase.co` vrnil **DNS NXDOMAIN (status 3)**,
kar je potrjeno z [javno DNS poizvedbo](https://dns.google/resolve?name=slkxdrljuhxmesrhwsoc.supabase.co&type=A).
Dokaz je shranjen skupaj z rezultati. To pojasni trenutno nedosegljivost te storitve;
ne dokazuje njenega stanja ob starem zagonu. Za delujočo pravo prijavo mora skrbnik
obnoviti ustrezen Supabase projekt ali nastaviti veljavna `VITE_SUPABASE_URL` in
`VITE_SUPABASE_ANON_KEY` ter ponovno zgraditi frontend. To je odprto okoljsko odstopanje
OBS-01; uspeh lokalnega nadomestka ga ne zapre. Obstoječe `.env` datoteke in skrivnosti
pri tem popravku niso spremenjene.

## Izvedba in rezultati

Lokalno okolje: Python **3.12.3**, Node.js **24.15.0**, Selenium **4.52.0**, Chrome
**157.0.8103.50**, MongoDB **7.0** v začasnem kontejnerju. GitHub workflow predpisuje
Ubuntu 24.04, Python 3.13 in Node.js 24. Namizno okno je 1920 × 1080; mobilni preizkus
izmeri viewport 375 × 812 CSS px.

| Izvedba | Scenariji | Koraki PASS / FAIL | Pričakovani izhod |
|---|---|---|---|
| Osnovni zagon | TS-01 do TS-06: 6/6 PASS | 23 / 0 | 0 |
| Namerno pokvarjena rešitev | TS-01: FAIL v 1.1 | 4 / 1 | 1 |
| Obnovljena rešitev | TS-01: PASS | 5 / 0 | 0 |

Za namerno napako skripta začasno zamenja naslov `NIDiKo` z `NAMERNA NAPAKA` v
`frontend/index.html` in domači poti `frontend/src/app/PageTitleManager.tsx`, nato
ponovno zgradi aplikacijo. Napaka je torej v rešitvi; pričakovanje testa ostane enako.
Osnovni scenarij TS-01 pred spremembo uspe, po spremembi odpove korak 1.1, ostali
štirje koraki pa uspejo. Po obnovi izvornih datotek v `finally` in novi gradnji vseh
pet korakov ponovno uspe. Skupni suite zahteva **0 → 1 → 0** ter natančno določeno
odstopanje; poljubna odpoved infrastrukture ne zadostuje.

Trajni dokazi: [povzetek zaznave napake](assets/avtomatizirano-funkcionalno-testiranje/2026-11-11/mutation_summary.json),
[osnovni zapisnik](assets/avtomatizirano-funkcionalno-testiranje/2026-11-11/baseline/test_execution_summary.json),
[zapisnik z napako](assets/avtomatizirano-funkcionalno-testiranje/2026-11-11/intentional-defect/test_execution_summary.json)
in [ponovitev po obnovi](assets/avtomatizirano-funkcionalno-testiranje/2026-11-11/restored/test_execution_summary.json).
Poti slik v zapisnikih so relativne na njihove mape.

Dodatno preverjanje: **651/651 zalednih testov PASS**, vključno s **17 regresijskimi
testi poganjalnika**. Frontend lint: **0 napak, 21 obstoječih opozoril**. Gradnje
frontenda so uspešne; ostaja obstoječe opozorilo o velikosti JS paketa. `actionlint`
sprejme vse štiri workflow datoteke, `git diff --check` nima napak. Celotni izhodi so
v mapi dokazov. Novi GitHub Actions zagon v tej seji ni bil sprožen.

## Ponovitev in omejitve

[Navodila z ukazi za Windows in Linux](../backend/tests/functional/README.md) vključujejo
namestitev, zagon začasne baze, celotni suite, neposredni staging zagon ter regresijske
teste. Obstoječe poročilo prejšnje naloge in njegovi zgodovinski dokazi ostajajo veljavni
za svoj zagon; nova izvedba jih ne prepisuje.

Uspeh potrjuje navedenih šest tokov v opisanem okolju, ne vseh funkcij aplikacije,
pravilnosti vseh priporočil, delovanja zunanjega AI, dostopnosti ali uspešne prijave.
Pravo Supabase okolje ostaja odprto, dokler konfiguracija ni obnovljena in ročni
integracijski workflow ne uspe. Popravki in preverjanje so pripravljeni s pomočjo
OpenAI Codex; dokument ne trdi, da sta jih člana ekipe osebno potrdila.
