# Avtomatizirano funkcionalno testiranje – NIDiKo

Datum: **5. 11. 2026**. Pregledana revizija: `873ca8933ca3f9848c043beb2a4396508a0a814e`.

## Izbira orodja in vključitev

Uporabljen je **Selenium WebDriver za Python**, ker projekt že vsebuje Python/FastAPI in šest Selenium scenarijev za React vmesnik. Chrome deluje brez grafičnega vmesnika (`--headless=new`); Selenium Manager poskrbi za gonilnik. Namestitev: `python -m pip install -r backend/requirements.txt`. Za ta pregled je bilo orodje nameščeno v ločeno lokalno virtualno okolje: Python 3.12.6, Selenium 4.52.0, Chrome 157.0.8103.38.

Polni staging test potrebuje Chrome, omrežni dostop, frontend, API, MongoDB z obstoječimi vsebinami in dosegljiv Supabase Auth. Uporablja vsebine `up_001`, `mod_014`, `ue_036`; posebna testna baza v tem workflowu ni vzpostavljena. Rezultati so JSON, PNG in izhodna koda 0/1. CI po namestitvi počaka na UI in API, zažene vseh šest scenarijev ter ob uspehu ali neuspehu shrani artefakte in povzetek. Manjkajoči koraki ne pomenijo uspeha.

Dodano opravilo v `ci.yml` gradi lokalni frontend in izvede **prijavni funkcionalni test s kontroliranim odgovorom Auth**. Ne potrebuje prave baze ali prijavnih ključev. Preveri obrazec, prevod napake, ostanek na `/login` in odsotnost shranjene seje. To preverjanje ne potrjuje dosegljivosti pravega Supabase; polni staging E2E ostaja ločen in uporablja pravo storitev.

## Ugotovljena vzroka padca

[Izvirni GitHub Actions zagon](https://github.com/McTehno/NIDiKo/actions/runs/41881074832) je izvedel 23 korakov: **21 PASS, 2 FAIL**, uspešni so bili štirje od šestih scenarijev. Chrome se je uspešno zagnal. Commit je spremenil samo staging workflow in vanj vključil že obstoječe teste.

| Korak | Dokaz in vzrok | Ukrep |
|---|---|---|
| TS-03.3 | Namesto pričakovane zavrnitve prijave se izpiše splošna napaka. Objavljeni JS in lokalna konfiguracija uporabljata `slkxdrljuhxmesrhwsoc.supabase.co`; 5. 11. DNS vrne NXDOMAIN, neposredni SDK poskus pa `AuthRetryableFetchError`, status 0, `ENOTFOUND`. | Obnoviti Supabase projekt ali nastaviti delujoč projekt in ustrezne ključe; nato ponovno zgraditi in namestiti frontend. |
| TS-06.2 | `StaleElementReferenceException` med navigacijo. Klik se že ponavlja, branje naslova po React izrisu pa ni bilo zaščiteno. | Tudi med preverjanjem ciljne strani ponovno poiskati elemente in ob zastareli referenci počakati na naslednji poskus. Napačen URL ali manjkajoči naslov še vedno povzročita FAIL. |

DNS in SDK dokaz potrjujeta stanje ob tem pregledu. Ker izvirni CI ne vsebuje omrežnega odgovora Auth, ni mogoče z gotovostjo dokazati, da je bil 4. 11. vzrok popolnoma enak. Najverjetnejša razlaga je nedosegljiv zunanji Auth. Iz samega DNS ni mogoče ugotoviti, ali je projekt ustavljen, izbrisan ali je naslov napačen.

Popravljeno je tudi čakanje na staging: po izteku poskusov sedaj vrne napako, preverja še API s testno vsebino ter omejuje trajanje posameznih zahtevkov in celotnega opravila.

## Izvedeni preizkusi in namerna napaka

Dokazi so v [assets/avtomatizirano-funkcionalno-testiranje/2026-11-05](assets/avtomatizirano-funkcionalno-testiranje/2026-11-05/).

| Preizkus | Rezultat |
|---|---|
| Regresije poganjalnika, vključno z zastarelimi elementi in napačno ciljno stranjo | **8 PASS** |
| Celoten TS-06 na lokalnem frontendu, pravi brezglavi Chrome | **3/3 koraki PASS** |
| Prijavni UI, kontrolirani HTTP 400 `invalid_credentials` | **PASS**, izhod 0 |
| V implementaciji `LoginPage.tsx` je prevod zavrnitve začasno spremenjen v `NAPAKA MUTACIJE` | **FAIL**, izhod 1; skripta zazna napačno obvestilo |
| Izvorna datoteka povrnjena, isti prijavni test ponovljen | **PASS**, izhod 0 |
| Prijavni test nad produkcijsko gradnjo s testnimi nastavitvami CI | **PASS**, izhod 0 |
| `npm run build` in `npm run lint` | Uspeh; obstoječe opozorilo velikosti JS in 21 lint opozoril, brez lint napak |
| YAML, Bash sintaksa vseh 23 korakov in obe izhodni veji staging readiness | Uspeh |

Mutacija je bila vnesena v aplikacijo, ne v pričakovanje testa, in je odstranjena. Navodila za ponovitev so v `backend/tests/functional/README.md`. Pri regresijskem zagonu brez celotnega backend okolja je pytest izpisal še opozorilo o nenaloženem `pytest-asyncio`; vseh osem sinhronih testov je uspelo.

## Preostalo delo in omejitve

**Polni staging E2E še ni potrjen kot uspešen.** Lokalni neposredni dostop brezglavega brskalnika do staging IP je vrnil `ERR_BLOCKED_BY_CLIENT`, zato je TS-06 preverjen lokalno. GitHub CI ni bil ponovno zagnan: spremembe niso pushane.

Za odpravo zunanjega vzroka je treba v Supabase preveriti stanje projekta, urediti `VITE_SUPABASE_URL` in `VITE_SUPABASE_ANON_KEY` ter na strežniku ponovno zgraditi frontend (Vite vrednosti vgradi med gradnjo; sam restart ne zadostuje). Pri menjavi projekta je treba uskladiti tudi backend preverjanje JWT, vključno z `SUPABASE_JWT_SECRET`. Nato ponoviti vseh šest staging scenarijev in priložiti novi JSON/PNG zapisnik. Sprejemno merilo ostaja **6/6 scenarijev PASS**.

Viri: [Selenium – zastarele reference](https://www.selenium.dev/documentation/webdriver/troubleshooting/errors/#staleelementreferenceexception), [Supabase – vrste napak](https://supabase.com/docs/guides/auth/debugging/error-codes).
