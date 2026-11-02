# Poročilo sistemskega testiranja NIDiKo

**Status: predloga; test na stagingu še ni izveden.** Spodnja polja niso rezultati.

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
