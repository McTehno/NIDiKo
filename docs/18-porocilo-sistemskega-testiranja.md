# Poročilo sistemskega testiranja NIDiKo

**Status: pilot izveden; vzdržljivostni preizkus s prekinitvijo generatorja poteka.** Zagon se nadaljuje brez ponovitve. Ne predstavlja osmih neprekinjenih ur obremenitve.


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

## Glavni vzdržljivostni zagon s prekinitvijo — poteka

Identifikator: `20261102T104244Z`; začetek 10:42:44 UTC oziroma 11:42:44 lokalno.
100 aktivnih mest, 40 z AI in 5 z glasovno pomočjo; izvirni profil s premori
15–35 s in prvotno načrtovanimi osmimi urami ciljne obremenitve. Nov sklop 15.000 sintetičnih profilov,
začetni glasovni predpomnilnik 16 zapisov po pilotu. Testna koda commit
`bedfae125544eedcff55989cd26bafc38ceb1d9b`.

Rezultati se sproti zapisujejo na generatorju v mapo `20261102T104244Z`, meritve
staginga v `/var/tmp/nidiko-perf/main-20261102`. Vključena sta preprečevanje
samodejnega spanja generatorja in nadzornik, ki po koncu poskusi prenesti meritve,
obnoviti prvotno bazo ter odstraniti premor namestitev. Uspeh obnove je treba
potrditi iz nadzornega dnevnika. Sintetični profili ostanejo za pregled do čiščenja.
Končne čase, kriterije in sklep dopolnimo po dejanskem zaključku.

## Odstopanje izvedbe: neaktivnost generatorja

Med pregledom 2. 11. 2026 okoli 13:31 po slovenskem času smo v izvornih dogodkih
odkrili vrzel med **12:36:23 in 13:27:04 lokalno** oziroma 11:36:23–12:27:04 UTC:
približno **50 minut in 41 sekund** brez dogodkov populacije generatorja. Ločene
meritve virov generatorja imajo v istem obdobju približno 3046-sekundno vrzel.
Pred tem je zabeležena še približno 78-sekundna vrzel med 12:35:00 in 12:36:18
lokalno. Časi so povzeti iz dogodkov; ne dokazujejo natančnega trenutka zadnje
zahteve pred prekinitvijo ali prve po njej.

Vzrok prekinitve ni potrjen. Pregled izbranih Windows dogodkov ni potrdil spanja.
Odsotnost meritev ni dokaz izpada strežnika: ob pregledu se backend ni ponovno
zagnal, generator pa je znova beležil 100 aktivnih mest. Istočasna odsotnost
dogodkov zahtev in meritev virov je omejitev izvajanja testa.

Ob pregledu je bilo v celotnem zagonu približno 3030 zahtev in 51 neuspešnih
zahtev z oznako HTTP 0, torej brez veljavnega odgovora HTTP. Teh napak brez
dodatnih dokazov ne pripisujemo aplikaciji ali Azure storitvam. Podatki so
vmesni, ne končna statistika. Približno 197 MB RAM in 0 ponovnih zagonov
backenda sta prav tako posnetek ob pregledu, ne meritev celotnega obdobja.

**Odločitev ekipe:** isti zagon nadaljujemo do njegovega predvidenega konca.
Testa ne začenjamo znova, ne ponastavljamo statistike in ne podaljšujemo režima
z namenom, da bi vrzel prikazali kot neprekinjeno osemurno obremenitev. Prvotni
načrt in kriteriji ostanejo ohranjeni kot izhodišče; odstopanje je izrecno priznano.

### Obravnava rezultatov po zaključku

- Ločeno navedemo celoten pretečeni čas, načrtovano ciljno fazo, ugotovljene vrzeli
  ter časovne intervale z dokazi o dejanski aktivnosti generatorja.
- Aktivni čas ocenimo iz dogodkov in časovnega pokritja; od osmih ur ne odštejemo
  samo največje vrzeli in rezultata ne predstavimo kot natančno izmerjeno aktivno
  trajanje. Preverimo tudi druge vrzeli in dejansko doseženo populacijo.
- Na grafih vrzeli označimo kot manjkajočo obremenitev oziroma manjkajoče podatke.
  Manjkajočega odzivnega časa ne prikažemo kot nič in krivulj prek vrzeli ne razlagamo
  kot neprekinjeno izmerjenega delovanja.
- Ohranimo vse izvorne vzorce in napake. Skupne rezultate označimo kot rezultate
  celotnega prekinjenega zagona; dodatno lahko prikažemo rezultate znotraj jasno
  navedenih aktivnih intervalov. Morebitnih izključitev ne izvajamo tiho.
- Zahteve, ki časovno segajo čez prekinitev, in napake HTTP 0 obravnavamo posebej.
  Brez dokazov jih ne razglasimo za napake aplikacije ali brezhibne odgovore.
- Samodejna ocena `INVALID` ostane veljavna glede na prvotni pogoj neprekinjene
  ciljne obremenitve. To ne izniči vseh zbranih vzorcev; ti so uporabni za presojo
  odzivnosti in opaženega obnašanja v dokumentiranih aktivnih intervalih.
- Časovne in tehnične kriterije ocenimo ločeno od veljavnosti trajanja. Pragov
  400 ms, 7 s, 3 s in deležev uspešnosti zaradi prekinitve ne spreminjamo.

**Omejitev sklepa:** izvedbo opišemo kot vzdržljivostni preizkus s prekinitvijo
generatorja. Ne trdimo, da je sistem prestal osem neprekinjenih ur ciljne obremenitve
ali da neaktivnost dokazuje stabilnost sistema pod obremenitvijo. Ponovitve v
okviru te izvedbe ne načrtujemo. Končni sklep temelji na dejansko zbranih dokazih.

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
Načrt: 100 aktivnih uporabnikov, 40 % z AI in 5 % z glasovno pomočjo, 8 ur ciljne obremenitve. Izvedba vključuje dokumentirano prekinitev generatorja in se ne ponovi.

| Podatek | Rezultat |
|---|---|
| Identifikator in UTC interval | `20261102T104244Z`; začetek 10:42:44 UTC, konec še ni potrjen |
| Dejansko dosežena obremenitev in trajanje | 100 aktivnih mest v opaženih aktivnih intervalih; prekinitev približno 51 minut in dodatna krajša vrzel; končni časovni obseg se še določi |
| Število začetih in uspešno zaključenih reševanj | ni izvedeno |
| Uspešnost in p99 običajnih zahtev | ni izmerjeno |
| Največji čas AI in prekoračitve 7 s | ni izmerjeno |
| Glasovni predpomnilnik, časi API in prenosa | ni izmerjeno |
| Razvoj porabe virov in okrevanje | ni izmerjeno |
| Opažene omejitve baze in zunanjih storitev | ni izmerjeno |
| Ocena kriterijev | neprekinjena 8-urna obremenitev ni potrjena; končna presoja odzivnosti po zaključku |
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
