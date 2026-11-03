# Poročilo sistemskega testiranja NIDiKo

**Skupno poročilo vzdržljivostnega in stresnega testiranja (2. in 3. 11. 2026) — zaključeno.**

Sistemsko testiranje rešitve NIDiKo je obsegalo dve neodvisni, a metodološko usklajeni preverjanji na enakem staging okolju:
1. **Osemurni vzdržljivostni test (1. član ekipe, 2. 11. 2026):** preverjanje dolgotrajne stabilnosti pri stalni obremenitvi 100 aktivnih uporabnikov.
2. **Večstopenjski stresni test (2. član ekipe, 3. 11. 2026):** določitev meje zmogljivosti, dinamike degradacije odzivnosti ob stopnjevanju od 20 do 220 uporabnikov ter analiza okrevanja.

**Skupna ocena:** Oba testa sta potrdila **izjemno visoko tehnično stabilnost** (99,985 % uspešnost pri vzdržljivosti in 100,0 % pri stresnem testu brez sesutja strežnika ali izpada storitev). Hkrati sta oba testa prejela formalno oceno **FAIL glede strogih časovnih kriterijev (SLA)**: običajni API-ji (`/api/assessments/evaluate` in pod večjo obremenitvijo `/api/questionnaires`) ter občasni AI odgovori so presegli vnaprej postavljene prage 400 ms oziroma 7 s.

---

## 1. Del: Osemurni vzdržljivostni test (1. član ekipe)

### Namen, orodje in okolje

Preverjali smo stabilnost reševanja vprašalnika ob dolgotrajni mešani uporabi običajnih API-jev, besedilnega AI pomočnika in glasovne pomoči. Izbrali smo Locust 2.47.0: uporabniške poteke je mogoče zapisati v Pythonu, simulirati premore in rezultate ločiti po skupinah zahtev. To je vzdržljivostni test; največje zmogljivosti sistema nismo iskali.

| Podatek | Izvedena konfiguracija |
|---|---|
| Staging | CX23, 2 vCPU, približno 4 GB RAM; javni HTTP dostop |
| Aplikacija | Docker; FastAPI/Uvicorn, en proces; React frontend |
| Zunanje odvisnosti | MongoDB; Azure OpenAI, Speech in Blob Storage |
| Aplikacijski commit | `6853f9d77d04477745943885cc6c08e5dd5ab3e6` |
| Testni commit ob začetku | `9040255757f74cfaa8cc8840dd2442a7cbf66fde`; delovna kopija ob začetku čista |
| Generator | ločen Windows prenosnik, en proces Locusta |
| Vsebina | učna pot `up_001`, 14 vprašanj DA/NE |
| Izolacija | namenska baza `psi_up_staging_perf_retry_20261102`, 15.000 novih sintetičnih profilov |
| Glasovni predpomnilnik | 21 začetnih zapisov, kopiranih iz prve testne baze |

Staging je med testom uporabljal namensko bazo; prvotnih profilov iz `psi_up` nismo spreminjali. Namestitve so bile začasno zadržane z `STAGING_DEPLOY_PAUSED=true`. Generator ni porabljal virov CX23. Manifest, profil in podatkovni povzetek so v [dokazih vzdržljivostnega testa](assets/system-testing/20261102T131105Z/README.md).

### Scenarij in kriteriji pred izvedbo

Uporabnik pridobi vprašalnik, bere vprašanja s premori 15–35 s in na koncu odda vse odgovore za ocenjevanje. Po zaključenem poteku aktivno mesto dobi nov profil. Od 100 mest jih 40 uporablja AI pomočnika, pet od teh tudi enkrat na reševanje glasovno pomoč. Uporabnik AI pošlje 1–20 sporočil z uteženo porazdelitvijo, povprečno 4,06 načrtovanega sporočila na tak potek; po pomoči sledi dodatnih 10–25 s branja. Deleži veljajo za aktivna mesta, ne nujno za vse zaključene poteke. To so predpostavke, ne meritve dejanske uporabe.

Obremenitev smo povečevali za enega uporabnika na sekundo; po doseženih 100 mestih je sledilo pet minut ogrevanja, osem ur ciljne obremenitve in dve minuti opazovanja po odstranitvi obremenitve.

Kriteriji: vsaj 99,9 % tehnično uspešnih veljavnih odgovorov v vsaki skupini; pri pridobitvi in oddaji vprašalnika vsaj 99 % vseh zahtev uspešnih v največ 400 ms; **vse** zahteve AI uspešne v največ 7 s do celotnega odgovora. Pri pripravljeni glasovni pomoči sta bili postavljeni ločeni meji 3 s za API in 3 s za celoten prenos posnetka. Za prvo ustvarjanje glasu časovni prag ni bil določen. Pragov po meritvah nismo spreminjali. Podrobnosti so v [prvotnem načrtu](17-nacrt-sistemskega-testiranja.md).

### Izvedba in sledljivost

Vsi spodnji lokalni časi veljajo za Europe/Ljubljana, 2. 11. 2026 (UTC + 1).

| Izvedba | Identifikator | Potek in obravnava |
|---|---|---|
| Pilot | `20261102T103826Z` | 11:38:26–11:40:59; 20 mest, skrajšani premori, 120 s ciljne faze; preverjen celoten potek, FAIL zaradi časov |
| Prvi glavni zagon | `20261102T104244Z` | 11:42:44–14:05:40; približno 51-minutna in dodatna krajša vrzel generatorja, nato izklop prenosnika; INVALID, arhiviran ločeno |
| Ponovitev | `20261102T131105Z` | 14:11:05–22:19:47; ciljna faza **14:17:46–22:17:46**, natanko 28.800 s |

Ponovitve nismo združevali s prvim zagonom. Preverjanje dogodkov ponovitve potrjuje 100 mest v vseh vzorcih ciljne populacije; največji razmik med zaporednima vzorcema je 1,71 s. Razmik meritev generatorja je največ 10,15 s. Zaključni zapis, vse zahtevane skupine in celotno trajanje so prisotni, brez neveljavnih vrstic ali napak izvajanja scenarija. To potrjuje izmerjeno časovno pokritje; ne pomeni, da je vseh 100 mest vsak trenutek pošiljalo zahtevo.

### Rezultati vzdržljivostnega testa

**Celoten zagon:** 26.865 zahtev, štiri neuspešne (vse pri AI), uspešnost **99,9851 %**. Začelo se je 7.750 reševanj, 7.650 jih je uspešno doseglo oddajo; 100 potekov je bilo ob odstranitvi obremenitve še aktivnih. Ti niso neuspešne oddaje. Uspešna oddaja tudi ne pomeni, da je vsa pomoč v poteku izpolnila svoje kriterije.

**Samo osemurna ciljna faza:** 26.583 zahtev, štiri neuspešne, uspešnost **99,9850 %**, povprečno 0,923 zahteve/s. Spodnja tabela uporablja izvorne čase te faze. Delež »v meji« šteje uspešne pravočasne zahteve med vsemi zahtevami skupine.

| Skupina | Zahteve | Napake | Uspešnost | Uspešne v časovni meji | p99 [ms] | Največ [ms] | Ocena |
|---|---:|---:|---:|---:|---:|---:|---|
| Pridobitev vprašalnika | 7.617 | 0 | 100 % | 92,02 % do 400 ms | 852,56 | 1.936,48 | FAIL |
| Oddaja in ocenjevanje | 7.617 | 0 | 100 % | 91,73 % do 400 ms | 725,80 | 1.438,04 | FAIL |
| AI pomočnik | 10.713 | 4 | 99,9627 % | 99,19 % do 7 s | 6.881,30 | 12.257,03 | FAIL |
| Pripravljen glasovni API | 318 | 0 | 100 % | 100 % do 3 s | 825,09 | 1.043,39 | PASS* |
| Celoten prenos zvoka | 318 | 0 | 100 % | 100 % do 3 s | 841,90 | 1.819,72 | PASS* |

\* Glasovni skupini imata manj kot 1.000 vzorcev; rezultat opisuje opažene zahteve in ne dokazuje dolgoročne 99,9-odstotne zanesljivosti. V ponovitvi so bili vsi glasovni API odgovori iz predpomnilnika; prvo ustvarjanje je bilo opaženo v pilotu, ne obremenjeno v glavnem testu.

Kriterij tehnične uspešnosti 99,9 % je izpolnjen v vsaki skupini. Pri AI je 83 uspešnih odgovorov preseglo 7 s, štiri dodatne zahteve pa niso dobile veljavnega odgovora HTTP (`HTTP 0` v testnem dnevniku). AI p99 je pod 7 s, vendar je bil dogovorjeni kriterij meja za **vse** zahteve, zato AI dobi FAIL.

![Odzivni časi vzdržljivostnega testa po petminutnih intervalih](assets/system-testing/20261102T131105Z/odzivni-casi.png)

### Infrastruktura in obnova po vzdržljivostnem testu

V 2.377 vzorcih stanja je bil backend isti vsebnik in v stanju `running`; ponovnega zagona med merjenjem nismo opazili. Docker CPU je v ciljni fazi povprečno znašal 5,78 %, največ 30,12 % (na dveh jedrih lahko doseže 200 %). Gostitelj je imel najmanj 2,31 GiB razpoložljivega RAM in približno 6,96 GiB prostega diska.

Backend RAM je v ciljni fazi znašal 127,9–262,7 MiB. Povprečje prvih desetih minut je bilo 149,9 MiB, zadnjih desetih 259,8 MiB. Rast se je po približno 2,5 ure večinoma ustalila okoli 250–263 MiB. Po dveh minutah brez obremenitve je ostalo približno 261,9 MiB.

Generator je imel povprečno 4,85 % sistemske porabe CPU in največ 29,4 %; metrike ne kažejo trajnega CPU nasičenja generatorja.

![Poraba virov in pokritje populacije](assets/system-testing/20261102T131105Z/infrastruktura.png)

Nadzornik je ob **22:20:02** potrdil prenos infrastrukturnih meritev, obnovo prvotne konfiguracije in baze `psi_up` ter odstranitev premora CI/CD. Po arhiviranju je bilo odstranjenih 35.000 sintetičnih profilov; prvotnih uporabnikov je ostalo natanko 29.

---

## 2. Del: Večstopenjski stresni test (2. član ekipe)

### Namen in razlika od vzdržljivostnega testa

Medtem ko vzdržljivostni test preverja stabilnost pri konstantni obremenitvi v časovnem razponu osmih ur, je bil namen večstopenjskega stresnega testa:
1. **Določiti dinamiko degradacije sistema** ob postopnem povečevanju števila sočasnih aktivnih uporabnikov od 20 do 220 mest.
2. **Identificirati točko preobremenitve (breaking point)**: ločeno točko kršitve kriterijev kakovosti (SLA) in točko tehnične odpovedi (napake, sesutje backenda, OOM ali zavrnitev povezav).
3. **Preveriti sposobnost okrevanja (recovery)**: ali si sistem po znižanju obremenitve z 220 na 20 uporabnikov takoj opomore na izhodiščno odzivnost.

### Konfiguracija okolja in uporabniški model

Okolje je bilo popolnoma primerljivo z vzdržljivostnim testom za zagotavljanje konsistence ugotovitev:
- **Staging strežnik:** CX23 (Hetzner VPS), 2 vCPU, ~4 GB RAM, Docker kontejner z enim Uvicorn delovnim procesom.
- **Uporabniški potek:** Učna pot `up_001` s 14 vprašanji tipa DA/NE.
- **Podatkovna izolacija:** Pripravljenih 5.000 novih sintetičnih profilov v namenski zbirki, nedotaknjenih prvotnih 29 profilov v `psi_up`.
- **Natančni deleži mest (SlotManager):** Vsak trenutek natanko 40 % aktivnih mest z AI pomočnikom in 5 % aktivnih mest z glasovno pomočjo (podmnožica AI), dinamično prilagojeno tudi med stopnjevanjem in zmanjševanjem števila uporabnikov.
- **Uteženi klici AI:** Število sporočil na reševanje iz seznama `[1, 2, 3, 4, 5, 8, 12, 20]` z utežmi `[20, 20, 20, 15, 10, 7, 5, 3]` (teoretično povprečje 4,06 klica/reševanje).
- **Varnostni nadzor (OverloadMonitor):** Drseče 60-sekundno okno napak z avtomatskim prehodom na okrevanje, če bi delež napak presegel 10 % v enem oknu ali 5 % v dveh zaporednih oknih (z vsaj 20 zahtevami).

### Izvedeni profil obremenitve

Stopnje so bile izvedene po vnaprej potrjenem [načrtu stresnega testiranja](19-nacrt-stresnega-testiranja.md). Prehod med stopnjami je potekal s stopnjo 2 uporabnika na sekundo; merjenje stabilnih 10 minut vsake stopnje se je začelo šele po doseženi polni populaciji.

| Faza / Stopnja | Ciljna mesta | Izmerjeno trajanje | Število zahtev | RPS | Delež napak |
|---|---:|---:|---:|---:|---:|
| Ogrevanje (Warmup) | 20 | 300,9 s (5 min) | 16 | 0,05 | 0,0 % |
| Stopnja 1 | 20 | 600,6 s (10 min) | 116 | 0,19 | 0,0 % |
| Stopnja 2 | 40 | 600,3 s (10 min) | 199 | 0,33 | 0,0 % |
| Stopnja 3 | 60 | 600,8 s (10 min) | 307 | 0,51 | 0,0 % |
| Stopnja 4 | 100 | 600,3 s (10 min) | 489 | 0,81 | 0,0 % |
| Stopnja 5 | 140 | 600,3 s (10 min) | 707 | 1,18 | 0,0 % |
| Stopnja 6 | 180 | 600,3 s (10 min) | 963 | 1,60 | 0,0 % |
| Stopnja 7 | 220 | 600,7 s (10 min) | 1.199 | 2,00 | 0,0 % |
| Okrevanje (Recovery) | 20 | 600,1 s (10 min) | 106 | 0,18 | 0,0 % |
| Ohladitev (Cooldown) | 0 | 120,0 s (2 min) | 0 | 0,00 | 0,0 % |
| **Skupaj (vključno s prehodi)** | **do 220** | **5.452 s (1 h 30 min 52 s)** | **4.448** | **0,82** | **0,00 %** |

Zagon se je začel 3. 11. 2026 ob 12:04:30 po slovenskem času (11:04:30 UTC) in zaključil ob 13:35:22 (12:35:22 UTC) s kodo 0. Varnostna zasilna ustavitev se med zagonom ni sprožila.

### Odzivni časi po stopnjah obremenitve

V spodnji tabeli so prikazani točni 99. percentili odzivnih časov (`p99` v milisekundah) ter delež zahtev, ki so izpolnile vnaprej določene časovne meje (SLA: 400 ms za običajne API-je, 7.000 ms za AI pomočnika, 3.000 ms za predpomnjen glasovni API in prenos zvočnega posnetka).

| Stopnja | Uporabniki | Vprašalnik p99 [ms] (<400ms) | Ocenjevanje p99 [ms] (<400ms) | AI pomočnik p99 [ms] (<7s) | Glasovni API p99 [ms] (<3s) | Zvočni prenos p99 [ms] (<3s) | Ocena stopnje |
|---|---:|---:|---:|---:|---:|---:|---|
| **Stopnja 1** | 20 | 384 ms (100 %) | 567 ms (87,2 %) | 6.708 ms (100 %) | 316 ms (100 %) | 902 ms (100 %) | **FAIL (SLA)** |
| **Stopnja 2** | 40 | 339 ms (100 %) | 555 ms (96,2 %) | 7.239 ms (97,6 %) | 318 ms (100 %) | 956 ms (100 %) | **FAIL (SLA)** |
| **Stopnja 3** | 60 | 390 ms (100 %) | 501 ms (90,8 %) | 3.885 ms (100 %) | 357 ms (100 %) | 987 ms (100 %) | **FAIL (SLA)** |
| **Stopnja 4** | 100 | 919 ms (97,1 %) | 867 ms (90,5 %) | 3.901 ms (99,0 %) | 352 ms (100 %) | 1.006 ms (100 %) | **FAIL (SLA)** |
| **Stopnja 5** | 140 | 659 ms (97,7 %) | 668 ms (90,2 %) | 2.866 ms (100 %) | 256 ms (100 %) | 996 ms (100 %) | **FAIL (SLA)** |
| **Stopnja 6** | 180 | 1.590 ms (89,5 %) | 1.150 ms (81,0 %) | 3.395 ms (100 %) | 400 ms (100 %) | 997 ms (100 %) | **FAIL (SLA)** |
| **Stopnja 7** | 220 | 929 ms (92,1 %) | 920 ms (83,5 %) | 4.697 ms (99,6 %) | 471 ms (100 %) | 978 ms (100 %) | **FAIL (SLA)** |
| **Okrevanje** | 20 | 170 ms (100 %) | 431 ms (97,1 %) | 5.454 ms (100 %) | 284 ms (100 %) | 896 ms (100 %) | **FAIL (SLA)** |

Interaktivni grafi in razporeditve so zbrani v samostojnem poročilu [report.html](assets/system-testing/20261103T110430Z/report.html).

### Analiza točk preloma (Breaking Points)

1. **Meja tehnične preobremenitve (Technical Breaking Point): NI BILA DOSEŽENA.**
   - Kljub stopnjevanju do 220 sočasnih aktivnih uporabnikov (več kot podvojena obremenitev osemurnega testa) je bilo vseh 4.448 poslanih zahtev obdelanih s statusnimi kodami HTTP 200/201 (0 napak, 0,00 % stopnja odpovedi).
   - Vsebnik Uvicorn se ni zrušil, OOM mehanizem Linuxa ni posredoval, zunanje storitve Azure OpenAI in Speech niso vrnile nobene napake 429 (Rate Limit).
   - Sistem CX23 je torej arhitekturno sposoben sprejeti promet 220 mešanih uporabnikov brez sesutja.

2. **Meja kriterijev kakovosti (SLA Breaking Point): DOSEŽENA V STOPNJI 1 (20 uporabnikov).**
   - **Končna točka za oddajo odgovorov (`POST /api/assessments/evaluate`)**: p99 odzivni čas je presegel mejo 400 ms že pri 20 uporabnikih (566,6 ms) in se pri višjih stopnjah gibal med 668 ms in 1.150 ms. Razlog je v sočasnem branju učne poti in shranjevanju rezultatov v MongoDB ter sinhroni validaciji.
   - **Pridobitev vprašalnika (`GET /api/questionnaires`)**: Do vključno 60 uporabnikov (Stopnja 3) je v celoti izpolnjeval kriterij 400 ms (p99 = 389,9 ms, 100 % uspešnih znotraj meje). Pri 100 uporabnikih (Stopnja 4) je p99 narasel na 918,6 ms, pri 180 uporabnikih pa dosegel 1.589,8 ms, saj se je pred enim Uvicorn delovnim procesom začela nabirati čakalna vrsta sočasnih zahtev.
   - **AI asistent (`POST /api/assessment-assistant/message`)**: Tipični p99 odzivni časi so se gibali med 2,8 s in 4,7 s (globoko pod mejo 7 s), vendar so se pri Stopnjah 2, 4 in 7 pojavili posamezni osamelci (max 7.238 ms pri 40 uporabnikih, 7.322 ms pri 100 uporabnikih in 8.181 ms pri 220 uporabnikih), kar je formalno kršilo pravilo, da morajo *vsi* AI odgovori prispeti v manj kot 7 s.
   - **Glasovne storitve**: Predpomnjen glasovni API (p99 med 256 ms in 471 ms) in prenos posnetka iz Azure Blob Storage (p99 med 896 ms in 1.006 ms) sta bila 100 % znotraj praga 3.000 ms na vseh stopnjah.

### Analiza okrevanja (Recovery)

Po zaključku Stopnje 7 (220 uporabnikov) je bila obremenitev znižana na 20 uporabnikov v 10-minutni fazi okrevanja:
- **Vprašalnik (`GET /api/questionnaires`)**: p99 se je takoj znižal na **170,1 ms** (kar je celo hitreje kot začetna Stopnja 1 z 384,3 ms, kar potrjuje vpliv ogretih predpomnilnikov in sproščenih povezav).
- **Ocenjevanje (`POST /api/assessments/evaluate`)**: p99 se je znižal z 919,5 ms nazaj na **430,8 ms** (97,1 % zahtev pod 400 ms).
- **AI asistent**: p99 se je vrnil na **5.453,6 ms** (100 % zahtev pod 7 s).
- **Delež napak**: Ostal na 0,0 %.
- **Zaključek okrevanja**: Sistem ne kaže nobenih znakov trajnih blokad, zasičenja povezav ali neobvladljivega kopičenja stanja. Ko se pritisk zmanjša, se odzivnost takoj povrne na nominalne ravni.

### Čiščenje podatkov in revizijska sled

Po zaključku stresnega testa je bilo izvedeno preverjanje in čiščenje:
- V bazi `psi_up` je bilo evidentiranih 506 sej in 3.448 sporočil, ustvarjenih med stresnim klicanjem pomočnika; vsi testni zapisi so bili izbrisani.
- Prvotnih uporabnikov v bazi `psi_up` je pred čiščenjem in po njem ostalo **natanko 29**.
- Iz testne baze `psi_up_staging_perf_stress_20261103` je bilo odstranjenih vseh 5.000 začasnih sintetičnih profilov.
- Dnevnik čiščenja je arhiviran v [`cleanup.log`](assets/system-testing/20261103T110430Z/cleanup.log), kontrolne vsote pa v [`SHA256SUMS-run.txt`](assets/system-testing/20261103T110430Z/SHA256SUMS-run.txt).

---

## 3. Skupni sklep in sinteza obeh delov sistemskega testiranja

Kombinacija osemurnega vzdržljivostnega testa in večstopenjskega stresnega testa nudi celovit in empirično dokazan vpogled v zmogljivost rešitve NIDiKo na obstoječi staging infrastrukturi.

### Glavne skupne ugotovitve

1. **Visoka strukturna stabilnost in odpornost:**
   - Obstoječa arhitektura (FastAPI + Docker + MongoDB Atlas + Azure) se je izkazala za izjemno stabilno.
   - Vzdrževala je 8 ur neprekinjenega delovanja pri 100 uporabnikih (99,985 % uspešnost) ter brez napak zdržala preizkus do 220 uporabnikov (100,0 % uspešnost).
   - Pomnilnik backenda se ustali okoli 260 MiB in ne kaže nenadzorovanega puščanja.

2. **Odzivnost običajnih API-jev kot primarno ozko grlo:**
   - Oba testa sta pokazala, da prag 400 ms za običajne API-je ni dosežen pri končni točki `/api/assessments/evaluate` (že pri 20 uporabnikih p99 presega 500 ms) in pri `/api/questionnaires` nad 60 uporabniki.
   - Glavni vzrok je arhitekturni: en sam delovni proces Uvicorn (`--workers 1`) v Docker vsebniku mora na 2 vCPU procesirati vse dohodne HTTP zahteve, izvajati Pydantic serializacijo in čakati na asinhrone I/O operacije baze MongoDB. Ob sočasnih oddajah se ustvari kratkotrajna vrsta, ki latenco dvigne na 500–1.200 ms.

3. **Zanesljivost zunanjih Azure storitev:**
   - Glasovna pomoč (predpomnjen API in Azure Blob prenos zvoka) deluje odlično in zanesljivo znotraj praga 3 sekund v 100 % primerov.
   - Besedilni pomočnik z Azure OpenAI `gpt-4o-mini` v povprečju odgovarja v 1,6–2,0 s (p99 tipično 3–4 s), vendar ima zunanji API občasne zamike (jitter) do 7–12 s, na katere aplikacija nima neposrednega vpliva.

### Tehnična priporočila za produkcijsko postavitev

Pred predajo sistema v redno uporabo na fakulteti priporočamo naslednje optimizacije:
1. **Povečanje števila delavcev Uvicorn:** Zagon kontejnerja z `uvicorn app.main:app --workers 2` ali `4` (glede na 2 vCPU jedri CX23), kar bo omogočilo vzporedno obdelavo zahtev in preprečilo čakanje v vrsti za `/api/questionnaires`.
2. **Optimizacija ocenjevanja vprašalnika:** Profiliranje poizvedb v `POST /api/assessments/evaluate`, dodajanje ustreznih indeksov v MongoDB ter predpomnjenje definicij učnih poti v pomnilniku backenda (in-memory cache namesto ponovnega branja iz baze ob vsaki oddaji).
3. **Prilagoditev SLA kriterijev realnosti oblačnih storitev:** Za LLM klice (`gpt-4o-mini`) je smiselno definirati SLA na ravni p95 < 5 s ali p99 < 7 s namesto zahteve, da *noben* klic ne sme preseči 7 s, saj oblačne storitve naravno vsebujejo občasne zamike omrežja ali obdelave.
