# Funkcionalni testni primeri in poročilo izvedbe – NIDiKo

**Predmet:** Zagotavljanje kakovosti
**Različica dokumenta:** 2, pregled in ponovitev 29. 10. 2026
**Podlaga pregleda:** commit `64ca55dfe0443ac2abecb0763d7af76840b2648f` in lokalna implementacija.
**Odgovorni osebi po obstoječi matriki:** Tilen Kek, Mihajlo Dejanović.
**Način izvedbe dopolnitve:** avtomatiziran zagon s pomočjo OpenAI Codex; ročna potrditev obeh članov s tem ni izkazana.

## 1. Obseg in dokumentacijska podlaga

Obstoječa oddaja že vsebuje šest scenarijev, matriko odgovornih oseb, korake in slikovne dokaze. Dopolnitev ohranja razdelitev treh scenarijev na vsakega od dveh navedenih članov ter odpravlja nekatera preverjanja, ki so lahko vrnila lažen PASS. Če je pri tej nalogi dejansko obvezna tričlanska ekipa, šest scenarijev ne zadošča: tretji član potrebuje svoje tri. Sestave ekipe ta pregled ni neodvisno preverjal.

| Dokument | Uporaba pri načrtovanju |
|---|---|
| [Pregled projekta](01-pregled-projekta.md) | Namen in ciljne funkcionalnosti. |
| [Arhitektura](03-arhitektura.md), [podatkovni model](05-podatkovni-model.md) | Povezava učna pot–modul–učna enota in zaledne odvisnosti. |
| [API](06-api-endpointi.md), [uporabniški tokovi](07-uporabniski-tokovi.md) | Iskanje, navigacija, prijava in vprašalnik. |
| [Zaslonski prikazi](08-zaslonski-prikazi.md), [testiranje](12-testiranje.md) | Vmesnik in ponovitev testov. |
| [Logika vprašalnika](14-logika-vprasalnika.md) | Veje Da/Ne in zaključevanje zaporednih vsebin. |

Ključne funkcionalnosti: **KF-01** iskanje in filtri; **KF-02** hierarhija vsebin; **KF-03** vprašalnik; **KF-04** prikaz samoocene/priporočila; **KF-05** prijava in zaščita dejanj; **KF-06** AI panel, navigacija in odzivni prikaz. Ker dokumentacija ne določa vseh preverljivih podrobnosti, so konkretna merila (npr. besedilo zavrnitve prijave) dopolnjena iz izvorne kode, navedene pri scenariju.

Predloga je projektna prilagoditev dokumentacije po zgledu **ISO/IEC/IEEE 29119-3:2021**. Uporablja identifikatorje, podlago/zahteve, predpogoje, podatke, korake, pričakovane in dejanske rezultate, popogoje ter zapisnik odstopanj. Polno besedilo standarda ni bilo preverjeno, zato ne trdimo formalne skladnosti. Standard opredeljuje predloge testne dokumentacije: [ISO](https://www.iso.org/standard/79429.html), [IEEE](https://standards.ieee.org/ieee/29119-3/7499/).

## 2. Matrika scenarijev in odgovornosti

| ID | Naziv | Odgovorna oseba | Prioriteta | Sledljivost | Rezultat ponovitve |
|---|---|---|---|---|---|
| TS-NIDIKO-01 | Iskanje, filtriranje po tipu in podrobnosti učne poti | Tilen Kek | Visoka | KF-01, KF-02 | PASS |
| TS-NIDIKO-02 | Vprašalnik učne poti z odgovoroma Da in Ne | Tilen Kek | Visoka | KF-03, KF-04 | PASS |
| TS-NIDIKO-03 | Zaščita shranjevanja, napačna prijava in vnos v AI panel | Tilen Kek | Visoka | KF-05, KF-06 | FAIL |
| TS-NIDIKO-04 | Prehod od modula do učne enote prek vmesnika | Mihajlo Dejanović | Visoka | KF-02 | PASS |
| TS-NIDIKO-05 | Vprašalnik posameznega modula | Mihajlo Dejanović | Srednja | KF-03, KF-04 | PASS |
| TS-NIDIKO-06 | Stran O nas, navigacija in mobilni viewport | Mihajlo Dejanović | Srednja | KF-06 | PASS |

## 3. Okolje, merila in omejitve

- Zagon: `2026-10-29T08:35:12.013497+01:00` do `2026-10-29T08:36:20.498608+01:00`; čas vsebuje UTC odmik.
- Ciljno okolje: `http://46.225.17.135`; izvorni zapis ga označuje kot staging. Identiteta objavljene Git revizije in posnetek baze nista znana.
- Python `3.12.6`, Chrome `156.0.8078.48`, Selenium 4.51.0, brezglavi način; namizno okno 1920 × 1080. Velikost okna ni isto kot notranji viewport.
- Vsak scenarij začne z očiščenimi piškotki, localStorage in sessionStorage. Obstoječi podatki učnih vsebin se ne spreminjajo. Vprašalnik se odda anonimno.
- **PASS:** izvedeni so vsi predvideni koraki in vsa njihova preverjanja so uspešna. **FAIL:** najmanj eno preverjanje ali izvedba ni uspešna. Manjkajoč korak ali napaka zagona ne moreta dati uspešnega scenarija. Vzrok FAIL je lahko aplikacija, okolje ali avtomatizacija; ne pomeni samodejno napake izdelka.
- Za sprejem vseh šestih scenarijev zahtevamo 6/6 PASS; pri odstopanju navedemo vzrok, dokaz in potreben ponovni preizkus. Ta merila ne pomenijo sprejema celotne aplikacije.
- Preverjamo prikaz samoocene, ne matematične pravilnosti vseh priporočil ali točne priporočene učne enote. Omrežni klic in čas API nista neposredno merjena.
- AI test preveri odprtje panela, vnos in omogočen gumb. Vprašanja ne pošlje in ne preveri odgovora ali Azure storitve.
- Mobilni test preveri velikost viewporta, vodoravni preliv in glavni naslov. Ne potrjuje celotne dostopnosti, prekrivanja vseh elementov ali delovanja na fizičnem telefonu.

## 4. Specifikacija primerov in zapisnik izvedbe

Specifikacija (podlaga, pogoji, podatki, akcije in pričakovanja) je ločena od stolpcev izvedbe (dejanski rezultat, čas, status, dokaz). Posnetki in JSON pripadajo samo spodnjemu zagonu.

### TS-NIDIKO-01: Iskanje, filtriranje po tipu in podrobnosti učne poti

- **Odgovorna oseba:** Tilen Kek; **cilj:** preveriti uporabniški tok, določen z naslednjimi koraki.
- **Testna podlaga:** Domača stran, iskanje in filtriranje v 07-uporabniski-tokovi.md; SearchPage.tsx in SearchFilters.tsx.
- **Predpogoji:** Anonimna seja; dostopna učna pot up_001 z naslovom »Iskanje informacij z umetno inteligenco«; vsi filtri izključeni.
- **Testni podatki:** Poizvedba: umetna inteligenca; filter: Učne poti; pričakovani cilj: /learning-paths/up_001.
- **Popogoji in čiščenje:** Odprta ciljna učna pot. Filter ostane v seji; seja se pred naslednjim scenarijem ponastavi.
- **Rezultat:** PASS; čas korakov 12.62 s.

| Korak | Akcija | Pričakovani rezultat | Dejanski rezultat | Čas (s) | Status | Dokaz |
|---|---|---|---|---:|---|---|
| 1.1 | Odpri /. | Naslov zavihka vsebuje NIDiKo. | Stran uspesno nalozena, naslov: 'NIDiKo' | 2.92 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts01_01_domaca_stran.png) |
| 1.2 | Klikni Iskanje v glavi. | URL vsebuje /search in iskalnik je dosegljiv. | Preusmeritev na http://46.225.17.135/search, prisotni filtri in vnosno polje | 2.33 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts01_02_iskanje_zacetno.png) |
| 1.3 | Vpiši umetna inteligenca. | Prikaže se najmanj ena kartica zadetka. | Najdenih 10 zadetkov, prvi: 'Iskanje informacij z umetno inteligenco \| UČNA POT \| #umetna inteligenca \| #UI \|' | 2.31 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts01_03_iskanje_zadetki.png) |
| 1.4 | Izberi filter Učne poti. | Filter je izbran; prikazani zadetki imajo tip UČNA POT in vključujejo ciljno pot. | Izbran filter Ucne poti; vsi prikazani zadetki imajo tip Ucna pot | 1.56 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts01_04_filtri_podrocja.png) |
| 1.5 | Klikni kartico Iskanje informacij z umetno inteligenco. | Odpre se točno /learning-paths/up_001. | Uspesna navigacija na http://46.225.17.135/learning-paths/up_001, naslov: 'Iskanje informacij z umetno inteligenco' | 3.50 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts01_05_podrobnosti_ucne_poti.png) |

### TS-NIDIKO-02: Vprašalnik učne poti z odgovoroma Da in Ne

- **Odgovorna oseba:** Tilen Kek; **cilj:** preveriti uporabniški tok, določen z naslednjimi koraki.
- **Testna podlaga:** 14-logika-vprasalnika.md, razdelek o zaporednih vsebinah; QuestionnairePage.tsx.
- **Predpogoji:** Anonimna seja; pot up_001 s pripadajočim vprašalnikom; dosegljivo zaledje.
- **Testni podatki:** up_001; prvo vprašanje: Da; drugo vprašanje: Ne.
- **Popogoji in čiščenje:** Vrnitev na /learning-paths/up_001 in prikazana sekcija Samoocena; lokalni napredek se pred naslednjim scenarijem izbriše.
- **Rezultat:** PASS; čas korakov 14.20 s.

| Korak | Akcija | Pričakovani rezultat | Dejanski rezultat | Čas (s) | Status | Dokaz |
|---|---|---|---|---:|---|---|
| 2.1 | Odpri up_001 in klikni Odpri vprašalnik. | Prehod na /assessment in prikaz vprašanja. | URL: http://46.225.17.135/assessment?target_type=learning_path&target_id=up_001, vprasanje: 'Razumem osnovni koncept umetne inteligence.' | 5.49 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts02_01_vprasalnik_vstop.png) |
| 2.2 | Na prvo vprašanje odgovori Da. | Na voljo je gumb Naslednjo. | Odgovor zabelezen, omogocen prehod 'Naslednjo →' | 1.43 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts02_02_vprasalnik_odgovor_da.png) |
| 2.3 | Klikni Naslednjo. | Prikaže se naslednje vprašanje; njegovo besedilo je zabeleženo v zapisniku. | Uspesen prehod, novo vprasanje: 'Znam prepoznati primere umetne inteligence v vsakdanjem življenju.' | 2.36 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts02_03_vprasalnik_vprasanje_2.png) |
| 2.4 | Odgovori Ne. | Na voljo je gumb Zaključi. | Prikazan gumb 'Zaključi →' za oddajo samoocene | 1.33 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts02_04_vprasalnik_odgovor_ne.png) |
| 2.5 | Klikni Zaključi. | Vrnitev na /learning-paths/up_001; prisotna sekcija Samoocena. | Preusmeritev na http://46.225.17.135/learning-paths/up_001, prisotna sekcija Samoocena: True | 3.59 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts02_05_rezultat_samoocene.png) |

### TS-NIDIKO-03: Zaščita shranjevanja, napačna prijava in vnos v AI panel

- **Odgovorna oseba:** Tilen Kek; **cilj:** preveriti uporabniški tok, določen z naslednjimi koraki.
- **Testna podlaga:** 07-uporabniski-tokovi.md; LoginPage.tsx (prevod Invalid login credentials); DetailActions in LearningPathAssistantBox.
- **Predpogoji:** Anonimna seja; dostopen Supabase Auth; e-poštni naslov testnega računa ne obstaja. To je predpostavka, ne administrativno preverjeno dejstvo.
- **Testni podatki:** up_001; neveljaven_uporabnik@test.si; geslo NepravilnoGeslo123!; osnutek vprašanja: Kaj obsega ta učna pot?
- **Popogoji in čiščenje:** Neuspešna prijava ostane na /login. Nato se odpre up_001 in v AI panel vnese osnutek; vprašanje se ne pošlje. Seja se počisti.
- **Rezultat:** FAIL; čas korakov 12.12 s.

| Korak | Akcija | Pričakovani rezultat | Dejanski rezultat | Čas (s) | Status | Dokaz |
|---|---|---|---|---:|---|---|
| 3.1 | Na up_001 klikni Shrani za pozneje. | Vidno opozorilo, da je potrebna prijava. | Modal 'Za to dejanje se moraš prijaviti' se uspesno prikaze | 2.58 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts03_01_auth_dialog.png) |
| 3.2 | V opozorilu klikni Prijavi se. | Odpre se /login. | Uspesna navigacija na http://46.225.17.135/login, prisoten prijavni obrazec | 2.23 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts03_02_login_obrazec.png) |
| 3.3 | Vnesi navedene napačne podatke in oddaj prijavo. | Vidno je »Napačen e-poštni naslov ali geslo.« in URL ostane /login. Splošna napaka ne dokazuje pravilne zavrnitve podatkov. | Pricakovana zavrnitev podatkov, prikazano: Prišlo je do napake. Poskusite znova. | 1.81 | FAIL | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts-03_03_fail.png) |
| 3.4 | Ponovno odpri up_001, odpri AI panel in vpiši vprašanje. | Vrednost polja ustreza vnosu; gumb Pošlji vprašanje je omogočen. Brez preverjanja odgovora AI. | Panel uspesno aktiviran, vpisana poizvedba v polje 'Vprašaj pomočnika ...' | 5.50 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts03_04_ai_pomocnik_odprt.png) |

### TS-NIDIKO-04: Prehod od modula do učne enote prek vmesnika

- **Odgovorna oseba:** Mihajlo Dejanović; **cilj:** preveriti uporabniški tok, določen z naslednjimi koraki.
- **Testna podlaga:** 07-uporabniski-tokovi.md; LearningUnitVisualizer.tsx; podatkovna hierarhija v 05-podatkovni-model.md.
- **Predpogoji:** Anonimna seja; mod_014 z učnimi enotami; prvo vozlišče vodi na ue_036.
- **Testni podatki:** Modul mod_014: Analiza in obdelava podatkov; prvo vozlišče; cilj /learning-units/ue_036.
- **Popogoji in čiščenje:** Odprta učna enota ue_036; brez sprememb trajnih podatkov.
- **Rezultat:** PASS; čas korakov 6.55 s.

| Korak | Akcija | Pričakovani rezultat | Dejanski rezultat | Čas (s) | Status | Dokaz |
|---|---|---|---|---:|---|---|
| 4.1 | Odpri /modules/mod_014. | URL vsebuje /modules/mod_014 in prikazan je neprazen naslov modula. | Modul nalozen, naslov: 'Analiza in obdelava podatkov' | 2.54 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts04_01_modul_podrobnosti.png) |
| 4.2 | Pomakni se do prvega vozlišča učnih enot. | Obstajajo elementi button[data-lu-node]; prvo vozlišče po pomiku in čakanju postane vidno. | Zaznana vozlisca ucnih enot za modul 'Analiza in obdelava podatkov' (4 elementov) | 1.55 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts04_02_modul_ucne_enote.png) |
| 4.3 | Klikni prvo vozlišče učne enote. | Prehod skozi vmesnik na /learning-units/ue_036; prikazan neprazen naslov enote. | Ucna enota nalozena, naslov: 'Uvod v podatkovno modeliranje' | 2.46 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts04_03_ucna_enota_podrobnosti.png) |

### TS-NIDIKO-05: Vprašalnik posameznega modula

- **Odgovorna oseba:** Mihajlo Dejanović; **cilj:** preveriti uporabniški tok, določen z naslednjimi koraki.
- **Testna podlaga:** 14-logika-vprasalnika.md; QuestionnairePage.tsx in ModuleDetailPage.tsx.
- **Predpogoji:** Anonimna seja; modul mod_014 z zaporednimi vprašanji in dosegljivim zaledjem.
- **Testni podatki:** /assessment?target_type=module&target_id=mod_014; prvo vprašanje Da, naslednje Ne, če je prikazano.
- **Popogoji in čiščenje:** Vrnitev na /modules/mod_014 s sekcijo Samoocena; lokalni odgovori se pred naslednjim scenarijem počistijo.
- **Rezultat:** PASS; čas korakov 11.74 s.

| Korak | Akcija | Pričakovani rezultat | Dejanski rezultat | Čas (s) | Status | Dokaz |
|---|---|---|---|---:|---|---|
| 5.1 | Odpri vprašalnik modula mod_014. | URL vsebuje /assessment in prikazan je neprazen naslov vprašanja. | Nalozeno vprasanje modula: 'Razumem, kaj je podatkovni model in zakaj ga potrebujemo.' | 2.81 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts05_01_modul_vprasalnik_zacetek.png) |
| 5.2 | Izberi Da. | Na voljo je navigacijski gumb Naslednjo ali Zaključi. | Odgovor zabelezen, aktiven gumb 'Naslednjo →' | 1.47 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts05_02_modul_vprasalnik_da.png) |
| 5.3 | Nadaljuj; na naslednje vprašanje po potrebi odgovori Ne in zaključi. | Odpre se /modules/mod_014 in vidna je sekcija Samoocena. | Koncni URL: http://46.225.17.135/modules/mod_014 | 7.46 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts05_03_modul_ocena_rezultat.png) |

### TS-NIDIKO-06: Stran O nas, navigacija in mobilni viewport

- **Odgovorna oseba:** Mihajlo Dejanović; **cilj:** preveriti uporabniški tok, določen z naslednjimi koraki.
- **Testna podlaga:** 08-zaslonski-prikazi.md; Navbar.tsx; osnovni odzivni prikaz.
- **Predpogoji:** Anonimna seja; dosegljive strani /, /search, /about in /register; namizno okno 1920 × 1080.
- **Testni podatki:** /about; navigacijske poti /, /search, /about, /register; emuliran viewport 375 × 812 CSS px.
- **Popogoji in čiščenje:** Odprta stran /about; emulacija mobilnega viewporta je odstranjena, okno povrnjeno na namizno velikost.
- **Rezultat:** PASS; čas korakov 6.98 s.

| Korak | Akcija | Pričakovani rezultat | Dejanski rezultat | Čas (s) | Status | Dokaz |
|---|---|---|---|---:|---|---|
| 6.1 | Odpri /about. | URL vsebuje /about; prikazan je neprazen glavni naslov. | Stran 'O nas' nalozena, naslov: 'Prilagodljiv razvoj digitalnih kompetenc.' | 2.39 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts06_01_o_nas_namizje.png) |
| 6.2 | Zaporedoma klikni povezave za Domov, Iskanje, O nas in Registracijo; vrni se na /about. | Vsak klik vodi na pričakovano pot in prikazan je glavni naslov. | Zaznanih 9 povezav v navigaciji | 1.94 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts06_02_navigacija_glava.png) |
| 6.3 | Nastavi viewport 375 × 812 in zajemi sliko. | Izmerjen notranji viewport je 375 × 812; ni vodoravnega preliva in glavni naslov je viden. Prekrivanja in berljivosti s tem ne potrjujemo v celoti. | Izmerjen viewport: {'contentWidth': 360, 'height': 812, 'width': 375}; brez vodoravnega preliva; vizualni pregled prekrivanja je locen | 2.65 | PASS | [Slika](assets/funkcionalno-testiranje/2026-10-29/ts06_03_o_nas_mobilni_pogled.png) |

## 5. Zbirni rezultati in odstopanja

- Izvedenih korakov: **23**; **PASS 22**, **FAIL 1**.
- Scenariji: **5/6 PASS**.
- Seštevek trajanj korakov: **64.21 s**. Vključuje čakanja in zajem slik; ni meritev odzivnosti API. Celotno trajanje zagona vključuje še pripravo in čiščenje.
- Dokazi: [izvorni JSON zapisnik](assets/funkcionalno-testiranje/2026-10-29/test_execution_summary.json) in 23 slik; poti v JSON so relativne na mapo zapisnika.

| ID | Scenarij / resnost | Opažanje in pričakovano vedenje | Stanje / nadaljnji korak |
|---|---|---|---|
| OBS-01 | TS-NIDIKO-03 / srednja | Ob napačnih podatkih je prikazana splošna napaka namesto prevoda »Napačen e-poštni naslov ali geslo.« iz LoginPage.tsx. Sama splošna napaka ne dokaže pravilne avtentikacijske zavrnitve. | Odprto: preveriti odgovor Supabase Auth, konfiguracijo okolja in preslikavo napak; nato ponoviti 3.3. Izvornega vzroka ne pripisujemo aplikaciji brez dodatne diagnostike. |

Začetni poskus dopolnjene avtomatizacije je odkril tudi težave s čakanjem na animacije in zastarelimi elementi ter razliko med velikostjo okna in viewporta. Poganjalnik je bil popravljen in ponovljen; ta dokument poroča zadnjo izvedbo.

## 6. Primerjava z izvorno oddajo

Izvorni JSON z dne 27. 10. 2026 vsebuje 23 zapisov PASS, vendar ta rezultat velja le za takratna preverjanja. Filtri so bili zgolj prešteti; pri prijavi je manjkajoče opozorilo nadomestilo izmišljeno besedilo; zaključek modula, rezultat samoocene in mobilni prikaz niso bili ustrezno potrjeni. Zato prvotnih 100 % ni mogoče uporabiti kot dokaz vseh opisanih funkcionalnosti.

Iz prvotnega JSON dobimo **74,14 s** in **23 slik**, medtem ko je poročilo navajalo 75,2 s in 16 slik. Različne so bile tudi posamezne meritve v tabelah. Nova izvedba ima lasten zapisnik in dokaze; stare slike in JSON so ohranjeni v prvotni mapi in niso prepisani.

Odpravljene so neutemeljene trditve o brezhibnosti celotnega sistema, pravilnosti vseh priporočil, hitrosti API ter o formalni skladnosti s standardom. Popravek dokumenta ne pomeni, da sta navedena člana osebno verificirala novo izvedbo.

## 7. Ponovitev in preverjanje poganjalnika

Iz korena repozitorija po namestitvi zalednih odvisnosti in Chroma:

```powershell
python -m pip install -r backend/requirements.txt
python backend/tests/functional/run_functional_tests.py --base-url http://46.225.17.135
```

Privzeti izhod je nova mapa `test-results/<run-id>/`. Z `--output-dir` lahko določimo drugo **še neobstoječo** mapo. S tem preprečimo prepis dokazov. Izhodna koda je 0 samo ob šestih uspešnih scenarijih; pri neuspehu ali napaki zagona je 1. Ne uporabljamo `python -O`, ker izklopi preverjanja assert. Testov nad zunanjim okoljem ne vključujemo samodejno v vsak PR brez nadzora testnih podatkov in razpoložljivosti storitev.

Lokalno preverjanje samega poganjalnika brez omrežja in brskalnika:

```powershell
python -m pytest backend/tests/functional/test_runner_regressions.py --confcutdir=backend/tests/functional -q
```

Izvedeno je bilo **5/5 uspešnih regresijskih testov**: manjkajoči koraki preprečijo PASS; obstoječi dokazi se ne prepišejo; napaka zagona ustvari zapisnik in izhod 1; napaka slike ne prekrije prvotne napake; en neuspešen korak povzroči neuspešen scenarij.

## 8. Sklep in uporaba AI

Dokument vsebuje šest specificiranih in dejansko ponovno izvedenih scenarijev. Doseženih je 5/6 PASS; merilo 6/6 ni izpolnjeno zaradi OBS-01. Odstopanje ostaja del poročila in ga je treba po odpravi ponovno preizkusiti. Uspeh omejenega nabora ne pomeni potrditve celotne rešitve.

Pri prvotni oddaji je bila navedena pomoč Google Antigravity / Gemini. Pri tem pregledu so bili analiza, popravki, avtomatiziran zagon in priprava dopolnjenega poročila izvedeni s pomočjo OpenAI Codex. Pred oddajo naj člana preverita odgovornosti, podatke o ekipi in rezultate; izjava o njunem osebnem pregledu ni dodana brez potrditve.
