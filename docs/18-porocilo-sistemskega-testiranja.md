# Poročilo sistemskega testiranja NIDiKo

**Status: pilot izveden; osemurni test teče.** Končni rezultati vzdržljivosti še niso znani.


## Izvedeni pilot — 2. 11. 2026

Identifikator: `20261102T103826Z`, UTC 10:38:26–10:40:59 (lokalno 11:38:26–11:40:59).
Staging commit `6853f9d77d04477745943885cc6c08e5dd5ab3e6`; CX23, 2 vCPU,
približno 4 GB RAM, Docker in en proces Uvicorn. Zahteve z zunanjega Windows
generatorja prek javnega staging naslova. Staging je začasno preusmerjen na
ločeno bazo `psi_up_staging_perf_20261102`; obstoječih 29 uporabniških profilov
v prvotni bazi `psi_up` nismo spreminjali. Izbrana pot `up_001`, 14 vprašanj DA/NE.

Pilot: 20 aktivnih mest, 8 z AI, eno tudi z glasovno pomočjo; dodajanje 2/s,
10 s ogrevanja, 120 s ciljne obremenitve, 10 s okrevanja. Premori so skrajšani
na 1–2 s za preverjanje celotnega poteka; to ni realistični profil glavnega testa.

V ciljni fazi:

| Skupina | Vzorcev | Uspešnih | Delež znotraj časovne meje | Največ ms |
|---|---:|---:|---:|---:|
| Pridobitev vprašalnika | 91 | 100 % | 62,64 % pod oziroma do 400 ms | 3112,17 |
| Oddaja in ocenjevanje | 91 | 100 % | 54,95 % pod oziroma do 400 ms | 2184,13 |
| AI pomoč | 103 | 100 % | 99,03 % do 7 s | 7669,57 |
| Glasovni API, pripravljeno | 1 | 100 % | 100 % do 3 s | 293,49 |
| Glasovni API, ustvarjanje | 1 | 100 % | brez dogovorjenega časovnega praga | 3854,82 |
| Prenos posnetka | 2 | 100 % | 100 % do 3 s | 1851,35 |

**Ocena pilota: FAIL zaradi časovnih kriterijev.** Vse skupine so bile izmerjene,
obremenitev dosežena in ciljno trajanje zaključeno. Tehničnih napak ni bilo.
V celotnem pilotu se je začelo 111 reševanj in uspešno zaključilo 91; preostalih
20 je bilo še aktivnih ob odstranitvi obremenitve. Ne gre za 20 neuspešnih oddaj.
Vzorci, zlasti glasovni, so majhni; pilot ni dokaz osemurne stabilnosti.
Opazovani backend je porabljal približno 112 MB RAM in imel 0 ponovnih zagonov.
To je posnetek stanja, ne končna presoja razvoja porabe skozi čas.

## Glavni vzdržljivostni zagon — poteka

Identifikator: `20261102T104244Z`; začetek 10:42:44 UTC oziroma 11:42:44 lokalno.
100 aktivnih mest, 40 z AI in 5 z glasovno pomočjo; izvirni profil s premori
15–35 s in osmimi urami ciljne obremenitve. Nov sklop 15.000 sintetičnih profilov,
začetni glasovni predpomnilnik 16 zapisov po pilotu. Testna koda commit
`bedfae125544eedcff55989cd26bafc38ceb1d9b`.

Rezultati se sproti zapisujejo na generatorju v mapo `20261102T104244Z`, meritve
staginga v `/var/tmp/nidiko-perf/main-20261102`. Vključena sta preprečevanje
samodejnega spanja generatorja in nadzornik, ki po koncu poskusi prenesti meritve,
obnoviti prvotno bazo ter odstraniti premor namestitev. Uspeh obnove je treba
potrditi iz nadzornega dnevnika. Sintetični profili ostanejo za pregled do čiščenja.
Končne čase, kriterije in sklep dopolnimo po dejanskem zaključku.

## Skupno okolje

| Podatek | Vrednost |
|---|---|
| Staging in konfiguracija CX23 | dopolni po preverjanju |
| Aplikacijski commit | ni določeno |
| Testni commit in orodje | dopolni; načrtovan Locust 2.47.0 |
| Baza in zunanje storitve | dopolni brez poverilnic |
| Izbrani vprašalnik in število vprašanj | ni določeno |

## Vzdržljivostni test — odgovorni za infrastrukturo

Načrt: [scenarij in kriteriji](17-nacrt-sistemskega-testiranja.md).
100 aktivnih uporabnikov, 40 % z AI in 5 % z glasovno pomočjo, 8 ur ciljne obremenitve.

| Podatek | Rezultat |
|---|---|
| Identifikator in UTC interval | ni izvedeno |
| Dejansko dosežena obremenitev in trajanje | ni izvedeno |
| Število začetih in uspešno zaključenih reševanj | ni izvedeno |
| Uspešnost in p99 običajnih zahtev | ni izmerjeno |
| Največji čas AI in prekoračitve 7 s | ni izmerjeno |
| Glasovni predpomnilnik, časi API in prenosa | ni izmerjeno |
| Razvoj porabe virov in okrevanje | ni izmerjeno |
| Opažene omejitve baze in zunanjih storitev | ni izmerjeno |
| Ocena kriterijev | ni ocenjena |
| Arhiv surovih rezultatov in grafi | ni ustvarjen |

Dodati pregled petminutnih intervalov, posebnosti vzorcev, napake in omejitve
interpretacije. Tehničnih preverjanj testnega orodja ne predstavljati kot rezultatov NIDiKo.

## Stresni test — drugi član ekipe

Ločen termin. Načrt, stopnje obremenitve, kriterije, izvajalca, identifikator
zagona in rezultate doda drugi član pred svojo izvedbo oziroma po njej.
Test še ni pripravljen in ni izveden v okviru te spremembe.

## Skupne ugotovitve

Dopolni po obeh izvedbah: dosežena zmogljivost, stabilnost, opažene omejitve,
predlogi izboljšav in omejitve veljavnosti zaključkov. Trenutno ni meritev,
na podlagi katerih bi lahko potrdili primernost infrastrukture za prihodnjo uporabo.
