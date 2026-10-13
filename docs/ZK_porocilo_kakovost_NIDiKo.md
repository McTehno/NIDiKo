# Poročilo o analizi kakovosti, standardih kodiranja in testiranju (Projekt NIDiKo)

**Predmet:** Zagotavljanje kakovosti  
**Projekt:** NIDiKo – Priporočilni sistem za izbiro učnih poti (Praktikum II)  
**Avtorja poročila (člana ekipe):** Tilen Kek, Mihajlo Dejanović  
*(Opomba: Pri razvoju projekta NIDiKo v okviru Praktikuma II so sodelovali 3 člani razvojne ekipe, to poročilo o kakovosti, standardih in testiranju pa pripravljava ter oddajava zgoraj navedena 2 člana ekipe).*  
**Datum analize:** Oktober 2026  

---

## Kazalo
1. [Uvod in namen analize](#1-uvod-in-namen-analize)
2. [Preverjanje in presoja dokumentacije za namestitev in vzpostavitev](#2-preverjanje-in-presoja-dokumentacije-za-namestitev-in-vzpostavitev)
   - [2.1 Individualna opažanja članov ekipe o namestitvi in vzpostavitvi](#21-individualna-opažanja-članov-ekipe-o-namestitvi-in-vzpostavitvi)
   - [2.2 Združena sinteza opažanj in analiza skladnosti različic orodij ter knjižnic](#22-združena-sinteza-opažanj-in-analiza-skladnosti-različic-orodij-ter-knjižnic)
   - [2.3 Vidiki več operacijskih sistemov (Windows, macOS, Linux)](#23-vidiki-več-operacijskih-sistemov-windows-macos-linux)
   - [2.4 Začetno stanje in zunanje odvisnosti](#24-začetno-stanje-in-zunanje-odvisnosti)
3. [Standardi kodiranja in arhitektura rešitve](#3-standardi-kodiranja-in-arhitektura-rešitve)
   - [3.1 Pregled standardov iz projektne dokumentacije](#31-pregled-standardov-iz-projektne-dokumentacije)
   - [3.2 Identificirana odstopanja v kodi](#32-identificirana-odstopanja-v-kodi)
   - [3.3 Izveden popravek kode (`backend/app/main.py`)](#33-izveden-popravek-kode-backendappmainpy)
4. [Pregled stanja testiranja in zagotavljanja kakovosti (QA)](#4-pregled-stanja-testiranja-in-zagotavljanja-kakovosti-qa)
   - [4.1 Pregledna tabela aktivnosti testiranja in QA](#41-pregledna-tabela-aktivnosti-testiranja-in-qa)
   - [4.2 Podroben opis aktivnosti in uporaba umetne inteligence (AI)](#42-podroben-opis-aktivnosti-in-uporaba-umetne-inteligence-ai)
5. [Varnostna presoja in analiza nadzora dostopa v staging okolju (Security & Authorization Audit)](#5-varnostna-presoja-in-analiza-nadzora-dostopa-v-staging-okolju-security--authorization-audit)
   - [5.1 Izpostavljenost Swagger UI in zalednih vrat 8000 na staging strežniku](#51-izpostavljenost-swagger-ui-in-zalednih-vrat-8000-na-staging-strežniku)
   - [5.2 Pregled stanja zaščite končnih točk (HTTP Bearer / JWT pokritost)](#52-pregled-stanja-zaščite-končnih-točk-http-bearer--jwt-pokritost)
   - [5.3 Identificirana varnostna odstopanja in ranljivosti v kodi](#53-identificirana-varnostna-odstopanja-in-ranljivosti-v-kodi)
   - [5.4 Analiza tveganj (OWASP API Security Top 10)](#54-analiza-tveganj-owasp-api-security-top-10)
   - [5.5 Priporočila in načrt sanacije (Remediation Plan)](#55-priporočila-in-načrt-sanacije-remediation-plan)
6. [Sklep in priporočila za nadaljnje delo](#6-sklep-in-priporočila-za-nadaljnje-delo)
7. [Izjava o uporabi generativnih orodij umetne inteligence](#7-izjava-o-uporabi-generativnih-orodij-umetne-inteligence)

---

## 1. Uvod in namen analize

V okviru vaj pri predmetu **Zagotavljanje kakovosti** nadaljujemo delo na projektu **NIDiKo**, razvitem pri predmetu Praktikum II. NIDiKo je spletna platforma z odzivnim React uporabniškim vmesnikom, FastAPI zaledjem (REST API), MongoDB Atlas podatkovno bazo, Supabase avtentikacijo ter Azure kognitivnimi storitvami (OpenAI, Speech Services).

Namen tega poročila je celovit pregled:
1. popolnosti, pravilnosti in medplatformske robustnosti projektne dokumentacije za namestitev in zagon,
2. skladnosti programske kode z vnaprej opredeljenimi standardi kodiranja ter izvedba potrebnega refaktoriranja,
3. stanja vseh obstoječih mehanizmov zagotavljanja kakovosti (avtomatski testi, CI/CD, statična analiza, ročna verifikacija) z identifikacijo vloge orodij umetne inteligence (AI),
4. varnostne presoje API vmesnikov, omrežne izpostavljenosti in nadzora dostopa (avtentikacija in avtorizacija) na staging/produkcijskem okolju.

---

## 2. Preverjanje in presoja dokumentacije za namestitev in vzpostavitev

Pregledana je bila krovna in specializirana dokumentacija:
* `README.md` v korenski mapi projekta
* `docs/04-vzpostavitev-razvojnega-okolja.md`
* `docs/02-tehnoloski-sklad.md`
* `backend/README.md` in `frontend/README.md`
* `docker-compose.dev.yml`, `docker-compose.prod.yml` in konfiguracijske predloge `.env.example`

### 2.1 Individualna opažanja članov ekipe o namestitvi in vzpostavitvi

Pri analizi dokumentacije in vzpostavitvi okolja sta oba člana ekipe (Tilen Kek in Mihajlo Dejanović) neodvisno sledila objavljenim navodilom za namestitev in lokalni zagon ter zabeležila svoja opažanja (pri razvoju celotnega projekta Praktikum II so sicer sodelovali 3 člani razvojne ekipe):

* **Mihajlo Dejanović (Razvoj uporabniškega vmesnika, odjemalsko okolje in namestitev / Frontend & DevOps):**
  * *Neskladje različic Node.js:* V Docker okolju (`frontend/Dockerfile` in `frontend/Dockerfile.dev`) je uporabljena različica `node:20-alpine`, medtem ko v CI cevovodu (`.github/workflows/ci.yml`) gradnja teče na Node.js različici `24`.
  * *Kritična napaka v navodilih za `VITE_API_BASE_URL`:* V dokumentu `docs/04-vzpostavitev-razvojnega-okolja.md` (vrstica 199) je kot privzet primer naveden `VITE_API_BASE_URL=http://localhost:8000`. Ker pa imajo vsi zaledni FastAPI usmerjevalniki predpono `/api`, frontend ob tej nastavitvi vrne napako 404 pri vseh poizvedbah. Delujoča vrednost v `frontend/.env` je `http://127.0.0.1:8000/api`.
  * *Neopredeljeni predpogoji za orodja:* V `docs/04-vzpostavitev-razvojnega-okolja.md` je med predpogoji zgolj zapisano *"Node.js"*, brez opredelitve minimalne podprte verzije (Node.js >= 20.x).
  * *Izrazita platformska pristranskost za Windows:* Vsa navodila za namestitev predpostavljajo Windows okolje (ukazi `copy`, obratne poševnice `\`, skripta `.ps1`, globalni `python`).

* **Tilen Kek (Razvoj zalednih storitev, podatkovna baza in varnost / Backend, Baza & Varnost):**
  * *Neskladje različic Pythona:* V `backend/Dockerfile` je določena osnova `python:3.11-slim`, medtem ko CI delotok (`.github/workflows/ci.yml`) in dokument `docs/02-tehnoloski-sklad.md` predpisujeta **Python 3.13**.
  * *Kodiranje datoteke `requirements.txt` (Kritična napaka v Docker gradnji):* Datoteka `backend/requirements.txt` je bila shranjena v kodiranju **UTF-16LE z oznako BOM (`0xFF, 0xFE`)**. Orodje `pip` znotraj Linux Docker vsebnika `python:3.11-slim` zato odpove z `UnicodeDecodeError`. Datoteko je bilo treba na novo shraniti v UTF-8 brez BOM.
  * *Omejenost navodil za virtualno okolje (`Activate.ps1`):* Navodila navajajo zagon izključno prek PowerShell skripte (`.\venv\Scripts\Activate.ps1`), pri čemer manjkajo navodila za sisteme POSIX (`source venv/bin/activate`) ter opozorilo glede privzetih varnostnih politik izvajanja skript v okolju Windows (`ExecutionPolicy`).
  * *Manjkajoča verzija za Pytest:* V tabeli `docs/02-tehnoloski-sklad.md` je pri orodju Pytest vpisana zgolj poševnica `/` (manjka verzija `9.0.2`, ki je določena v `backend/requirements.txt`).
  * *Prikrita odvisnost od oblačnih poverilnic in začetnega stanja baze:* Dokumentacija ne razmejuje nujnih spremenljivk od opcijskih (brez `MONGODB_URI` se celotna aplikacija takoj sesuje) ter ne vsebuje samodejnih inicializacijskih skript (seeding) za uvoz podatkov v MongoDB Atlas.
  * *Izpostavljenost produkcijskih vrat in Swagger UI:* Na staging strežniku (`http://46.225.17.135:8000`) so neposredno odprta vrata 8000 s celotnim interaktivnim Swagger UI-jem brez kakršnekoli avtentikacije.

---

### 2.2 Združena sinteza opažanj in analiza skladnosti različic orodij ter knjižnic

Združena analiza vseh članov ekipe razkriva natančno stanje skladnosti med objavljeno dokumentacijo, konfiguracijskimi datotekami, Docker definicijami in CI/CD cevovodom:

#### Primerjalna tabela skladnosti različic

| Tehnologija / Orodje | Dejansko v kodi in okolju | V `docs/02-tehnoloski-sklad.md` | V `docs/04-vzpostavitev...md` / `README.md` | Stanje skladnosti |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | **3.11** (`backend/Dockerfile`) <br> **3.13** (`.github/workflows/ci.yml`) | **3.13** | Brez navedbe verzije *(samo "Python")* | ❌ **Neskladno** (Docker 3.11 vs. CI/Docs 3.13) |
| **Node.js** | **20** (`frontend/Dockerfile`) <br> **24** (`.github/workflows/ci.yml`) | Brez navedbe verzije | Brez navedbe verzije *(samo "Node.js")* | ❌ **Neskladno** (Docker 20 LTS vs. CI 24) |
| **React & React DOM** | `^19.2.6` (`frontend/package.json`) | **19.2.6** | Omenjen brez verzije | ✅ **Skladno** |
| **TypeScript** | `~6.0.2` (`frontend/package.json`) | **6.0.2** | Omenjen brez verzije | ✅ **Skladno** |
| **Vite** | `^8.0.12` (`frontend/package.json`) | **8.0.12** | Omenjen brez verzije | ✅ **Skladno** |
| **Tailwind CSS** | `^4.3.0` (`frontend/package.json`) | **4.3.0** | Omenjen brez verzije | ✅ **Skladno** |
| **FastAPI** | `0.136.1` (`backend/requirements.txt`) | **0.136.1** | Omenjen brez verzije | ✅ **Skladno** |
| **Pydantic** | `2.13.4` (`backend/requirements.txt`) | **2.13.4** | Omenjen brez verzije | ✅ **Skladno** |
| **Uvicorn** | `0.46.0` (`backend/requirements.txt`) | **0.46.0** | Omenjen brez verzije | ✅ **Skladno** |
| **PyMongo** | `4.17.0` (`backend/requirements.txt`) | **4.17.0** | Omenjen brez verzije | ✅ **Skladno** |
| **Pytest** | `9.0.2` (`backend/requirements.txt`) | `/` *(manjka)* | Omenjen brez verzije | ⚠️ **Pomanjkljivo** v tabeli `02` |
| **Različica aplikacije** | Frontend `0.0.0` vs Backend `0.1.0` | Ni opredeljeno | Ni opredeljeno | ⚠️ **Neusklajeno** med podprojekti |

#### Ključne ugotovitve in neskladja:
1. **Dvojnost izvajalnih okolij za Python (Docker 3.11 vs. CI/Docs 3.13):**  
   Projekt se v vsebniku gradi na starejši podobi `python:3.11-slim`, medtem ko dokumentacija in GitHub Actions uporabljata Python 3.13. To ustvarja tveganje, da koda ali odvisnosti, ki uspešno prestanejo teste v CI okolju na Pythonu 3.13, odpovejo v Docker okolju na Pythonu 3.11.
2. **Dvojnost izvajalnih okolij za Node.js (Docker 20 vs. CI 24):**  
   Frontend vsebnik teče na Node.js 20 LTS, CI cevovod pa na najnovejši verziji Node.js 24. Za lokalni razvoj mora dokumentacija natančno predpisati minimalno podprto različico (Node.js >= 20.x).
3. **Kritična konfiguracijska napaka `VITE_API_BASE_URL` v navodilih:**  
   V `docs/04-vzpostavitev-razvojnega-okolja.md` navedena vrednost `http://localhost:8000` (brez `/api`) neposredno poruši komunikacijo frontenda z zaledjem, saj so vsi usmerjevalniki FastAPI registrirani z obvezno predpono `/api`.
4. **Kodiranje konfiguracijskih datotek (`requirements.txt`):**  
   Windows urejevalniki so `requirements.txt` shranili v UTF-16LE z BOM glavo, kar v Linux/Docker okolju povzroči neuspešno namestitev paketov s strani `pip`.

---

### 2.3 Vidiki več operacijskih sistemov (Windows, macOS, Linux)

Dokumentacija v trenutni obliki močno favorizira okolje Windows:

| Vidik | Trenutno v dokumentaciji (Windows) | Potrebno za Linux / macOS |
| :--- | :--- | :--- |
| **Priprava `.env`** | `copy backend\.env.example backend\.env` | `cp backend/.env.example backend/.env` |
| **Aktivacija okolja** | `.\venv\Scripts\Activate.ps1` | `source venv/bin/activate` |
| **Zagonske poti** | Uporaba obratnih poševnic `\` | Uporaba poševnic `/` |
| **Upravitelj paketov** | Predpostavlja globalni `python` | Pogosto zahteva `python3` in `python3-venv` |

*Zaključek:* Dokumentacijo je treba dopolniti z ločenimi navodili za POSIX (Linux/macOS) in Windows sisteme.

### 2.4 Začetno stanje in zunanje odvisnosti

Za uspešen prvi zagon projekt potrebuje:
1. **Node.js (>= v20 LTS ali v24)** in **Python (3.11 ali 3.13)**.
2. Vnaprej pripravljeno podatkovno zbirko v MongoDB Atlas z uvoženimi začetnimi podatki (v mapi `backend/data/` se nahajajo začetni šifranti in testni podatki, manjkajo pa avtomatske inicializacijske skripte, ki bi ob prvem zagonu bazo samodejno napolnile).
3. Supabase projekt z vklopljeno JWT avtentikacijo za preverjanje žetonov prijavljenih uporabnikov.

---

## 3. Standardi kodiranja in arhitektura rešitve

Standardi kodiranja in arhitekturna pravila projekta so bila v celoti pregledana neposredno iz obstoječe projektne dokumentacije v repozitoriju, predvsem iz dokumentov:
* `docs/10-pravila-poimenovanja-in-pisanje-kode.md`
* `backend/README.md` in `backend/CONTRIBUTING.md`
* `frontend/README.md` in `frontend/CONTRIBUTING.md`
* `docs/03-arhitektura.md`

### 3.1 Pregled standardov iz projektne dokumentacije

Na podlagi natančnega pregleda projektne dokumentacije in načel čistega oblikovanja programske opreme (Clean Code, DRY princip, večslojna arhitektura) so v projektu določena štiri osrednja pravila dobre inženirske prakse:

#### 1. Poimenovanje razredov, metod in spremenljivk (Naming Conventions)
* **Pomenljivost in domensko poimenovanje:** Vsa poimenovanja v kodi dosledno sledijo poslovni domeni projekta v angleškem jeziku (`learning_path`, `learning_unit`, `questionnaire`, `assessment`, `user_progress`) ter so opisna brez kriptičnih okrajšav.
* **Slovnična pravila:**
  * Razredi, podatkovni tipi in komponente se pišejo v pisavi `PascalCase` (npr. `LearningPathService`, `UserProgressResponse`, `Navbar`).
  * Metode in funkcije predstavljajo glagole ali glagolske zveze:
    * Python: `snake_case` (npr. `get_learning_path_by_id`, `calculate_topic_score`).
    * TypeScript: `camelCase` (npr. `fetchLearningUnits`, `submitQuestionnaire`).
  * Konstante se pišejo v pisavi `UPPER_SNAKE_CASE` (npr. `SEARCH_TYPE_ALIASES`, `DEFAULT_PAGE_SIZE`).
  * Boolove spremenljivke imajo obvezne predpone stanja (`is_completed`, `has_access`, `should_evaluate`).

#### 2. Način gnezdenja in zmanjševanje ciklomatične kompleksnosti (Nesting & Control Flow)
* **Pravilo zgodnjega vračanja (Early Return / Guard Clauses):** Namesto globoko vgnezdenih `if-else` stavkov koda najprej preveri robne in neveljavne pogoje ter nemudoma sproži izjemo ali vrne rezultat. S tem se preprečuje t.i. "piramidna koda" in ohranja ravna hierarhija izvajanja.
* **En nivo abstrakcije na funkcijo:** Ena funkcija ne sme hkrati izvajati nizkonivojskega parsiranja podatkov in visokonivojske orkestracije poslovnih pravil.

#### 3. Večslojna arhitektura in načelo ene odgovornosti (Single Responsibility Principle - SRP)
* **API sloj (`backend/app/api`):** Odgovoren izključno za validacijo vhodnih zahtevkov, branje HTTP parametrov in vračanje odgovorov. Vsebuje ničelno poslovno logiko.
* **Servisni sloj (`backend/app/services`):** Vsebuje celotno poslovno logiko, točkovanje in pravila odločanja. Ne komunicira neposredno s podatkovno bazo.
* **Podatkovni sloj (`backend/app/repositories`):** Edini sloj z neposrednim dostopom do MongoDB zbirke.
* **Podatkovni modeli (`backend/app/schemas`):** Strogo tipizirani Pydantic modeli za vhodne in izhodne podatkovne strukture.

#### 4. Komentiranje in docstringi (Clean Code komentarji)
* **Koda razloži "kaj", komentarji razložijo "zakaj":** Komentarji ne ponavljajo očitnih programskih korakov, temveč pojasnjujejo poslovna pravila, neintuitivne robne pogoje ali kompenzacijo specifik zunanjih storitev.
* **Obvezni docstringi:** Vsi razredi, javne metode in API endpointi morajo imeti strukturiran opis namena, parametrov in vračanih vrednosti.

---

### 3.2 Identificirana odstopanja v kodi

Z analizo celotne izvorne kode zaledja glede na dokumentirane standarde smo identificirali naslednja neskladja:
1. **Podvojeni uvozi (Dead / Redundant Imports):** V vstopni datoteki `backend/app/main.py` so se nahajali podvojeni uvozi usmerjevalnikov za asistente (`learning_path_assistant_router`, `module_assistant_router`, `learning_unit_assistant_router`), uvoženi dvakrat v dveh ločenih blokih kode.
2. **Podvojena registracija API usmerjevalnikov:** V osrednjem aplikacijskem objektu FastAPI so bili zgoraj navedeni usmerjevalniki za asistente registrirani dvakrat s ponavljajočimi se klici `app.include_router(...)`, kar je kršilo načelo DRY.
3. **Manjkajoči tipski pripisi in pomanjkljivi docstringi:** Korenski testni endpoint `read_root()` v `backend/app/main.py` ni vseboval vračanega tipa ter je bil brez pojasnjevalnega docstringa.
4. **Mrtva koda v API sloju:** V mapi `backend/app/api/` so se nahajale datoteke `competencies.py`, `competency_groups.py` in `recommendations.py`, ki v osrednji aplikaciji niso bile registrirane.

---

### 3.3 Izveden popravek kode (`backend/app/main.py`)

V skladu z navodili vaje smo definirane standarde kodiranja uveljavili s popravkom kode v osrednji vstopni datoteki zaledja `backend/app/main.py`:

* **Zakaj je bilo treba datoteko popraviti:**
  V datoteki `backend/app/main.py` so se nahajali podvojeni uvozi usmerjevalnikov za AI asistente v dveh ločenih blokih kode, poleg tega pa so bili ti usmerjevalniki z metodo `app.include_router(...)` registrirani kar dvakrat. To je povzročalo redundantno obremenitev usmerjevalne tabele in neposredno kršilo načelo DRY. Hkrati so bili uvozi knjižnice FastAPI razdrobljeni na več mestih, korenski testni endpoint `read_root()` pa ni imel določenega vračanega tipa ter pojasnjevalnega docstringa.

* **Kaj in kako se je popravilo:**
  * **Ureditev in konsolidacija uvozov (PEP 8 standard):** Vsi uvozi iz zunanje knjižnice FastAPI so bili združeni v enoten začetni blok, lokalni uvozi domenskih usmerjevalnikov in obravnavalnikov napak pa so bili logično preurejeni in očiščeni vseh podvojenih vrstic.
  * **Enotna registracija usmerjevalnikov (načelo DRY):** Odpravljeni so bili podvojeni klici registracije asistentov, tako da se vsak domenski usmerjevalnik zdaj v aplikacijo vključi točno enkrat z enotno predpono `/api`.
  * **Tipizacija in dokumentacija (Clean Code standard):** Korenskemu endpointu `read_root()` smo dodali ekspliciten tipski pripis vračane vrednosti (`dict[str, str]`) ter strukturiran slovenski docstring, ki pojasnjuje namen klica za preverjanje delovanja sistema.

* **Način preverjanja (verifikacija):**
  Pravilnost popravka smo potrdili z uspešnim uvozom aplikacijskega objekta (`python -c "from app.main import app"`), lokalnim zagonom strežnika Uvicorn ter uspešno izvedbo celotne zbirke avtomatskih testov (`pytest`).

---

## 4. Pregled stanja testiranja in zagotavljanja kakovosti (QA)

Projekt NIDiKo že vključuje visoko raven zagotavljanja kakovosti, zgrajeno na več nivojih testne piramide.

### 4.1 Pregledna tabela aktivnosti testiranja in QA

| Vrsta aktivnosti | Stanje | Pokriti del rešitve | Uporabljena orodja in ogrodja | Uporaba umetne inteligence (Orodje in način preverjanja) |
| :--- | :--- | :--- | :--- | :--- |
| **Avtomatsko enotsko testiranje (Unit testing)** | **Aktivno / Implementirano** (obsežno) | Poslovna logika (`services`): ocenjevalni mehanizem, določanje priporočene poti, predizpolnjevanje vprašalnikov, upravljanje napredka. | **Pytest 9.0.2**, **pytest-asyncio 1.3.0**, Python `unittest.mock` | **Uporabljena (Claude / ChatGPT):** Priprava začetnih testnih matric za robne pogoje točkovanja odgovorov. Rezultati so bili verificirani z ročnim pregledom logike in lokalnim zagonom `pytest`. |
| **Integracijsko API testiranje (API integration tests)** | **Aktivno / Implementirano** (42 testnih datotek) | Vsi REST API endpointi (`/api/learning-paths`, `/api/questionnaires`, `/api/assessments`, `/api/user-progress`, `/api/search` idr.). | **Pytest**, **HTTPX 0.28.1** (`AsyncClient`), FastAPI `TestClient` | **Uporabljena:** Generiranje simuliranih JSON zahtevkov in pričakovanih shem odgovorov. Verificirano z zagonom vseh 42 testnih modulov. |
| **Statična analiza kode in tipsko preverjanje** | **Aktivno** | Celotna frontend koda (React, TypeScript komponente, tipi in servisi). | **TypeScript compiler (`tsc`)**, **Vite build**, **ESLint (`eslint.config.js`)** | **Uporabljena:** Pomoč pri razreševanju kompleksnih TypeScript generikov v servisih. Verificirano z uspešnim zagonom `npm run build` (brez napak ali tipskih opozoril). Zagon `npm run lint` zabeleži 21 opozoril (predvsem `react-hooks/set-state-in-effect`), kar ponuja priložnost za nadaljnje refaktoriranje. |
| **Kontinuirana integracija (CI Pipeline)** | **Aktivno** | Celoten repozitorij ob vsakem `push` in `pull_request` dogodku na vejo `main`. | **GitHub Actions** (`.github/workflows/ci.yml`), Ubuntu Latest okolje | **Brez neposredne generacije:** Uporabljena zgolj za pregled sintakse delotoka. Verificirano z zelenimi statusi gradenj na GitHubu. |
| **Ročno funkcijsko testiranje (Manual Scenario Testing)** | **Aktivno / Dokumentirano** | Uporabniški tokovi: neprijavljen uporabnik, registracija/prijava prek Supabase, reševanje vprašalnika DA/NE, shranjevanje med priljubljene. | **Swagger UI** (`http://localhost:8000/docs`), spletni brskalniki Chrome / Firefox / Edge | **Uporabljena:** Priprava strukturiranih testnih scenarijev v dokumentu `12-testiranje.md`. Verificirano z ročnim preklikanjem s strani članov ekipe. |
| **Testiranje odzivnosti in uporabniške izkušnje (UI/UX Testing)** | **Aktivno** | Odzivni prelomi (mobilni, tablični, namizni pogled) in dostopnost vmesnika. | **Chrome DevTools Device Emulation**, **Tailwind CSS** breakpointi | **Uporabljena:** Pomoč pri optimizaciji UX sporočil in preprečevanju prelamljanja besedil. Verificirano z vizualno primerjavo na različnih ločljivostih. |
| **Avtomatsko celostno testiranje (End-to-End E2E)** | **V načrtu** (trenutno še ni implementirano) | Celotni tokovi v brskalniku od klika do vpisa v bazo. | Predvideno: **Playwright** ali **Cypress** | *Ni bila uporabljena.* |
| **Varnostni pregled avtorizacije in nadzora dostopa (Security Audit)** | **Izvedeno v okviru analize pri predmetu Zagotavljanje kakovosti** | Vsi API endpointi (`/api/users`, `/api/user-progress`, `/api/assessments`, AI pomočniki), JWT validacija in Docker konfiguracija. | **Ročni pregled kode (Code Review)**, **cURL**, **Swagger UI**, analitična matrika skladnosti z OWASP API Top 10 | **Uporabljena (Claude / ChatGPT):** Analiza poti izvajanja, identifikacija vrzeli v preverjanju pravic (BOLA/IDOR) in oblikovanje priporočil za odpravo ranljivosti. |

### 4.2 Podroben opis aktivnosti in uporaba umetne inteligence (AI)

1. **Testiranje zaledja s Pytest:**
   * Zaledje vsebuje kar **42 testnih datotek** s skupno **629 avtomatiziranimi testi**, ki se v celoti uspešno izvedejo v približno 4 sekundah (`629 passed`).
   * Testna zbirka je premišljeno strukturirana po arhitekturnih slojih v 5 ločenih mapah:
     * `tests/api/` (8 datotek): integracijsko testiranje REST API končnih točk in HTTP statusnih kod,
     * `tests/services/` (14 datotek): enotsko testiranje poslovne logike, točkovanja odgovorov ter določanja učnih poti,
     * `tests/repositories/` (8 datotek): testiranje podatkovnega sloja in operacij nad zbirkami MongoDB,
     * `tests/schemas/` (8 datotek): preverjanje veljavnosti in robnih pogojev Pydantic podatkovnih shem,
     * `tests/data/` (4 datoteke): verifikacija celovitosti in strukture začetnih JSON podatkov ter šifrantov.
   * Z uporabo `pytest-asyncio` se testirajo asinhroni klici, simulirajo se nepopolni podatki iz MongoDB baze in preverja se odpornost sistema na manjkajoča polja (defenzivno programiranje).
   * **Uporaba AI:** Orodja AI so bila uporabljena za pospešitev pisanja testnih podatkov (`fixtures`) in simulacij (mocking baze). Vsi generirani testi so bili deterministično preverjeni v CI cevovodu in pri lokalnem zagonu.
2. **Preverjanje frontenda (Build & Linter):**
   * Preverjanje se izvaja z `npm run build`, ki sproži `tsc -b` (TypeScript build). Ta preveri skladnost tipov podatkov med odjemalcem in strežnikom.
   * **Uporaba AI:** AI je pomagal pri uskladitvi TypeScript vmesnikov v `src/types/` z dejanskimi Pydantic shemami zaledja, s čimer so se odpravile napake neskladnosti podatkovnih struktur.
3. **GitHub Actions CI Workflow:**
   * Delotok teče na okolju `ubuntu-latest` in ima ločena opravila:
     1. `frontend-build`: namestitev odvisnosti z `npm ci` ter zagon `npm run build`.
     2. `backend-build`: priprava okolja Python 3.13, namestitev `requirements.txt` ter preverjanje veljavnosti uvoza aplikacije (`python -c "from app.main import app"`).
     3. `backend-tests`: zagon celotne zbirke testov z ukazom `python -m pytest --asyncio-mode=auto`.

---

## 5. Varnostna presoja in analiza nadzora dostopa v staging okolju (Security & Authorization Audit)

Pri pregledu kakovosti rešitve NIDiKo je bila izvedena celostna varnostna presoja delovanja zaledja, avtentikacijskih mehanizmov in omrežne konfiguracije v testnem/staging okolju. Rezultati razkrivajo pomembna varnostna odstopanja med načrtovano varnostno politiko in dejanskim stanjem v kodi.

### 5.1 Izpostavljenost Swagger UI in zalednih vrat 8000 na staging strežniku

V produkcijski/staging konfiguraciji vsebnika [`docker-compose.prod.yml`] je storitev zaledja opredeljena z neposrednim mapiranjem vrat:
```yaml
services:
  backend:
    container_name: nidiko_backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
```
Ker so vrata `8000` neposredno izpostavljena na vseh omrežnih vmesnikih gostitelja (`0.0.0.0:8000`), je zaledni strežnik FastAPI neposredno dostopen na javnem naslovu strežnika (npr. `http://46.225.17.135:8000`).

Ker ogrodje FastAPI privzeto generira interaktivno dokumentacijo OpenAPI, sta na javno dostopnih vratih 8000 brez kakršnekoli avtentikacije odprti:
* **Swagger UI dokumentacija:** `http://46.225.17.135:8000/docs`
* **ReDoc dokumentacija:** `http://46.225.17.135:8000/redoc`
* **Shema OpenAPI JSON:** `http://46.225.17.135:8000/openapi.json`

**Varnostno tveganje:**  
Javna izpostavljenost Swagger UI nepooblaščenim zunanjim uporabnikom ponuja popoln zemljevid vseh zalednih poti, vhodnih podatkovnih shem, parametrov ter interaktivni vmesnik (*"Try it out"*), preko katerega lahko napadalec neposredno iz brskalnika pošilja poizvedbe in preizkuša ranljivosti v avtorizaciji.

---

### 5.2 Pregled stanja zaščite končnih točk (HTTP Bearer / JWT pokritost)

S podrobnim pregledom vseh definiranih usmerjevalnikov v mapi [`backend/app/api/`] je bila izdelana celovita matrika stanja zaščite in avtentikacijskih mehanizmov:

| Modul / Pot (Endpoint) | HTTP metoda | Uporabljen mehanizem zaščite | Stanje avtentikacije | Ocena tveganja |
| :--- | :--- | :--- | :--- | :--- |
| **`/api/users/profile`** | `POST` | `Depends(get_current_user)` | **Zaščiteno (HTTP Bearer)**; preveri `sub == auth_user_id` | Nizko / Ustrezno |
| **`/api/users/by-auth/{auth_user_id}`** | `GET` | `Depends(get_current_user)` | **Zaščiteno (HTTP Bearer)**; preveri `sub == auth_user_id` | Nizko / Ustrezno |
| **`/api/users/{user_id}`** | `GET` | *Brez zaščite* | **ODPRTO (Nepooblaščen dostop)**; vrača celoten profil z napredkom | **KRITIČNO** (Uhajanje podatkov) |
| **`/api/users/{user_id}`** | `PUT` | *Brez zaščite* | **ODPRTO (Nepooblaščeno spreminjanje)**; BOLA / IDOR ranljivost | **KRITIČNO** (Integriteta podatkov) |
| **`/api/user-progress/{user_id}`** | `GET` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)**; preveri ujemanje uporabnika | Ustrezno na tem nivoju |
| **`/api/user-progress/{user_id}/ensure`** | `POST` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/save`** | `POST` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/unsave`** | `DELETE` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/favorite`** | `POST` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/unfavorite`** | `DELETE` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/complete`** | `POST` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/uncomplete`** | `DELETE` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/current-position`** | `PUT` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/user-progress/answers`** | `POST` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/assessments/evaluate`** | `POST` | *Brez zaščite* | **ODPRTO (Nepooblaščeno ocenjevanje)**; sprejme poljuben `user_id` v JSON | **KRITIČNO** (Vrivanje podatkov) |
| **`/api/assessments/latest`** | `GET` | `Depends(get_authenticated_local_user_id)` | **Zaščiteno (HTTP Bearer)** | Ustrezno |
| **`/api/questionnaires`** | `GET` | *Brez zaščite* (`user_id` kot opcijski parameter) | **DELNO ODPRTO**; ob podanem `user_id` razkrije odgovore drugega uporabnika | **VISOKO** (Uhajanje odgovorov) |
| **`/api/voice-help/question`** | `POST` | *Brez zaščite* | **ODPRTO**; proži klice v Azure OpenAI in Speech API | **VISOKO** (Finančno tveganje / DoS) |
| **`/api/*-assistant/message`** (4 asistenti) | `POST` | *Brez zaščite* | **ODPRTO**; proži klice v Azure OpenAI (LLM) | **VISOKO** (Zloraba virov / DoS) |
| **`/api/learning-paths`** | `GET` | *Brez zaščite* | **Javno dostopno** (katalog vsebin) | Ustrezno (javni podatki) |
| **`/api/modules`** | `GET` | *Brez zaščite* | **Javno dostopno** (katalog vsebin) | Ustrezno (javni podatki) |
| **`/api/learning-units`** | `GET` | *Brez zaščite* | **Javno dostopno** (katalog vsebin) | Ustrezno (javni podatki) |
| **`/api/search`** | `GET` | *Brez zaščite* | **Javno dostopno** (iskanje po vsebinah) | Ustrezno (javni podatki) |

---

### 5.3 Identificirana varnostna odstopanja in ranljivosti v kodi

Z analizo izvorne kode je bilo odkritih 7 specifičnih ranljivosti in arhitekturnih odstopanj:

#### 1. Zaobid zaščite napredka preko nezaščitenega `GET /api/users/{user_id}` (Excessive Data Exposure & BOLA)
V datoteki [`backend/app/api/users.py`](line 81) endpoint `get_user_by_id` nima nobene avtentikacijske odvisnosti:
```python
@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Uporabnik ni najden.")
    return user
```
V shemi [`backend/app/schemas/user_schema.py`](line 83) pa model `UserResponse` vključuje celotno vdelano strukturo uporabnikovega napredka:
```python
class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    auth_provider: Optional[str] = None
    auth_user_id: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    progress: UserProgress = Field(default_factory=UserProgress) # <-- VSEBUJE CELOTEN NAPREDEK
```
**Posledica:** Čeprav so vsi endpointi v `/api/user-progress/` strogo zaklenjeni z JWT žetoni, lahko nepooblaščen klicatelj zgolj s poznavanjem ali ugibanjem `user_id` preko `GET /api/users/{user_id}` pridobi celoten uporabnikov profil (ime, e-pošto, `auth_user_id`) in **vse njegove shranjene, priljubljene, zaključene vsebine ter odgovore na vprašalnike**. Zaščita na nivoju `/api/user-progress` je s tem popolnoma obidena.

#### 2. Nepooblaščeno spreminjanje profila preko `PUT /api/users/{user_id}` (Broken Object Level Authorization - BOLA / IDOR)
V [`backend/app/api/users.py`](line 98):
```python
@router.put("/{user_id}", response_model=UserResponse)
async def update_user_profile(
    user_id: str,
    request: UserUpdateRequest,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await user_service.update_user_profile(
        user_id=user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    ...
```
Endpoint nima nobene avtentikacije (`get_current_user` manjka) in ne preverja, ali je klicatelj lastnik profila. Poljuben napadalec lahko z eno samo `PUT` zahtevo prepiše ime in e-poštni naslov kateregakoli uporabnika v bazi podatkov.

#### 3. Neavtenticiran vpis podatkov pri ocenjevanju vprašalnikov (`POST /api/assessments/evaluate`)
V [`backend/app/api/assessments.py`](line 150):
```python
@router.post("/evaluate", response_model=AssessmentResultResponse)
async def evaluate_questionnaire_answers(
    request: QuestionnaireSubmitRequest,
    assessment_progress_service: AssessmentProgressService = Depends(
        get_assessment_progress_service
    ),
) -> AssessmentResultResponse:
    result = await assessment_progress_service.evaluate_and_update_progress(
        user_id=request.user_id,
        target_type=request.target_type,
        target_id=request.target_id,
        submitted_answers=[answer.model_dump() for answer in request.answers],
    )
    return result
```
Zahtevek sprejme poljuben `user_id` v telesu zahteve (`QuestionnaireSubmitRequest`) brez preverjanja avtentikacijskega žetona. Nepooblaščen klicatelj lahko pošilja lažne odgovore v imenu kateregakoli uporabnika in mu v bazi prepiše status zaključenih modulov, trenutno pozicijo ter rezultate samoocene.

#### 4. Neavtenticirano razkritje odgovorov v `GET /api/questionnaires`
V [`backend/app/api/questionnaires.py`](line 78) je parameter `user_id` neobvezen poizvedbeni parameter:
```python
if user_id:
    latest_explicit_answers = (
        await questionnaire_answers_service.get_latest_explicit_answer_maps(
            user_id=user_id
        )
    )
```
Ker endpoint ne preverja žetona prijavljenega uporabnika, lahko zunanji uporabnik pošlje npr. `GET /api/questionnaires?target_type=learning_path&target_id=lp-1&user_id=target_user_id` in v odgovoru neposredno prebere, kako je določen uporabnik odgovoril na vprašanja.

#### 5. Kritična opustitev preverjanja podpisa JWT v `app/core/security.py`
V osrednjem varnostnem modulu [`backend/app/core/security.py`](line 21) je v funkciji `get_current_user` zapisana implementacija:
```python
try:
    # Supabase may use ES256 or RS256 now. For local dev/prototype without a JWKS fetcher,
    # we can decode without verifying the signature if we trust the client.
    payload = jwt.decode(
        token,
        options={"verify_signature": False, "verify_aud": False}
    )
    return payload
```
Zaradi nastavitve `verify_signature: False` zaledje sploh ne preveri kriptografskega podpisa žetona. Posledično lahko napadalec lokalno ustvari poljuben JWT žeton z izmišljenim poljem `"sub": "katerikoli_id"` brez poznavanja skrivnega ključa, zaledje pa bo tak žeton sprejelo kot popolnoma verodostojen. To izniči varnost vseh sicer "zaščitenih" endpointov (vključno s celotnim `/api/user-progress`).

#### 6. Neomejeni in nezaščiteni klici plačljivih oblačnih storitev (AI asistenti in glasovna pomoč)
Endpointi:
* `/api/voice-help/question` (sinteza govora z Azure Speech in generiranje razlage z LLM)
* `/api/assessment-assistant/message`
* `/api/learning-path-assistant/message`
* `/api/module-assistant/message`
* `/api/learning-unit-assistant/message`

Vsi zgoraj navedeni endpointi so javno dostopni brez avtentikacije in nimajo implementiranega mehanizma za omejevanje pogostosti klicev (Rate Limiting). Ker vsaka zahteva sproži klic plačljivega modela (Azure OpenAI `gpt-5.4-nano` / Azure Speech Service), je sistem izpostavljen tveganju zlorabe virov (Denial of Wallet) in izčrpanju kvot.

#### 7. Razkritje podrobnosti internih napak (Information Disclosure)
V [`backend/app/api/voice_help.py`](line 46) splošni blok za obravnavo napak vrača:
```python
except Exception as error:
    import traceback
    traceback.print_exc()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"{type(error).__name__}: {str(error)}",
    ) from error
```
Vračanje surovega niza napake (`str(error)`) lahko nepooblaščenim klicateljem razkrije interne podatke o povezovalnih nizih, imenih Azure vsebnikov ali konfiguraciji infrastrukture.

---

### 5.4 Analiza tveganj (OWASP API Security Top 10)

Identificirane varnostne pomanjkljivosti se neposredno uvrščajo v mednarodno priznano lestvico varnostnih tveganj za spletne vmesnike (OWASP API Security Top 10 - 2023):

1. **API1:2023 – Broken Object Level Authorization (BOLA):**
   * *Prisotno pri:* `PUT /api/users/{user_id}`, `GET /api/users/{user_id}`, `POST /api/assessments/evaluate`, `GET /api/questionnaires?user_id=...`.
   * *Vpliv:* Možnost branja in spreminjanja tujih uporabniških računov in napredka zgolj z manipulacijo ID identifikatorja v URL-ju ali telesu zahteve.
2. **API2:2023 – Broken Authentication:**
   * *Prisotno pri:* `options={"verify_signature": False}` v `security.py`.
   * *Vpliv:* Popolna izguba zaupanja v identiteto klicatelja; možnost ponarejanja žetonov (Token Forgery).
3. **API3:2023 – Broken Object Property Level Authorization (Excessive Data Exposure):**
   * *Prisotno pri:* `UserResponse` v `GET /api/users/{user_id}`, ki vrača celoten `progress`.
   * *Vpliv:* Nepooblaščeno razkritje celotne zgodovine uporabnikovega učenja in odgovorov.
4. **API4:2023 – Unrestricted Resource Consumption:**
   * *Prisotno pri:* AI asistenti in glasovna pomoč brez avtentikacije in brez Rate Limiting omejitev.
   * *Vpliv:* Finančna škoda zaradi neomejene porabe Azure žetonov in potencialna nerazpoložljivost storitve (DoS).
5. **API8:2023 – Security Misconfiguration:**
   * *Prisotno pri:* Odprt port `8000:8000` na staging strežniku z javno dostopnim Swagger UI vmesnikom `/docs`.
   * *Vpliv:* Povečana napadalna površina in enostavno raziskovanje API ranljivosti.

---

### 5.5 Priporočila in načrt sanacije (Remediation Plan)

Za odpravo ugotovljenih varnostnih ranljivosti v okviru zagotavljanja kakovosti predlagamo naslednje konkretne ukrepe:

#### 1. Zavarovanje Swagger UI in zaprtje zalednih vrat v produkciji
V `backend/app/main.py` je treba generiranje Swagger dokumentacije pogojiti z okoljsko spremenljivko (npr. izklop v produkciji ali zaščita z HTTP Basic Auth):
```python
import os
from fastapi import FastAPI

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

app = FastAPI(
    title="NIDiKo API",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if ENVIRONMENT != "production" else None,
)
```
V `docker-compose.prod.yml` pa vrata `8000` umakniti iz javnega dostopa (`ports: - "8000:8000"` se odstrani), komunikacijo pa speljati izključno preko Nginx povratnega posrednika na standardnih vratih 80/443 znotraj internega Docker omrežja.

#### 2. Uveljavitev avtentikacije in ločitev javnih/zasebnih podatkov v `/api/users`
V `backend/app/api/users.py` je treba:
1. `GET /{user_id}` in `PUT /{user_id}` zakleniti z `Depends(get_current_user)` ter preveriti ujemanje uporabnika.
2. V `UserResponse` odstraniti občutljivo polje `progress` oziroma ustvariti ločeno shemo `UserPublicProfileResponse` (če je potreben javni prikaz imena) in `UserProfileResponse` za osebni profil:
```python
@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_user), # Zaščita z JWT
) -> UserResponse:
    # Preverjanje pravice dostopa: uporabnik lahko bere le svoj profil
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Uporabnik ni najden.")
    if user.get("auth_user_id") != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Dostop zavrnjen.")
    return user
```

#### 3. Zaščita `POST /api/assessments/evaluate`
V `assessments.py` zamenjati prosto posredovanje `request.user_id` z avtenticiranim klicem:
```python
@router.post("/evaluate", response_model=AssessmentResultResponse)
async def evaluate_questionnaire_answers(
    request: QuestionnaireSubmitRequest,
    user_id: str = Depends(get_authenticated_local_user_id), # Avtentikacija
    assessment_progress_service: AssessmentProgressService = Depends(get_assessment_progress_service),
) -> AssessmentResultResponse:
    # request.user_id se nadomesti z verificiranim user_id iz žetona
    result = await assessment_progress_service.evaluate_and_update_progress(
        user_id=user_id,
        target_type=request.target_type,
        target_id=request.target_id,
        submitted_answers=[answer.model_dump() for answer in request.answers],
    )
    return result
```

#### 4. Vključitev preverjanja podpisa JWT žetonov
V `backend/app/core/security.py` omogočiti preverjanje kriptografskega podpisa z uporabo `SUPABASE_JWT_SECRET` (algoritem `HS256`):
```python
payload = jwt.decode(
    token,
    key=SUPABASE_JWT_SECRET,
    algorithms=["HS256"],
    options={"verify_signature": True, "verify_aud": False}
)
```

#### 5. Uvedba omejevanja hitrosti (Rate Limiting) in zaščita AI modulov
Na vseh endpointih, ki komunicirajo z Azure kognitivnimi storitvami, uvesti:
* Zahtevo po veljavnem prijavnem žetonu (da anonimni roboti ne morejo sprožati poizvedb).
* Knjižnico `slowapi` za omejevanje na npr. največ 10 zahtev na minuto na uporabnika.

---

## 6. Sklep in priporočila za nadaljnje delo

Z analizo smo ugotovili:
1. **Dokumentacija:** Zagotavlja osnovo za postavitev, vendar jo je treba dopolniti s specifikami za sisteme POSIX (Linux/macOS), odpraviti napako pri vrednosti `VITE_API_BASE_URL` v `docs/04-vzpostavitev-razvojnega-okolja.md` ter poenotiti deklaracije različic orodij (Python, Node.js, Pytest).
2. **Kakovost kode:** Standardi kodiranja so bili v kodi večinoma dobro upoštevani. Odkrito odstopanje (podvojeni uvozi in registracije usmerjevalnikov v `backend/app/main.py`) je bilo z refaktoriranjem uspešno odpravljeno.
3. **Zagotavljanje kakovosti (QA):** Projekt ima že vzpostavljen robusten nabor enotskih in integracijskih testov (42 testnih datotek) ter delujoč avtomatiziran CI sistem z GitHub Actions.
4. **Varnostna presoja (Security QA):** Identificirana so bila kritična odstopanja pri avtorizaciji (BOLA/IDOR na `/api/users/{user_id}` in `/api/assessments/evaluate`, zaobid zaščite napredka, izklopljeno preverjanje podpisa JWT žetonov, javno izpostavljen Swagger UI na vratih 8000 ter nezaščiteni klici plačljivih AI storitev).

**Prednostna priporočila za naslednje korake:**
1. **Takojšnja sanacija varnostnih ranljivosti:** Implementacija predlaganih popravkov iz poglavja 5.5 (vključitev preverjanja podpisa JWT, zaščita končnih točk za uporabnike in ocenjevanje ter zaprtje javnih vrat 8000).
2. **E2E in varnostno testiranje:** Razširitev CI delotoka z avtomatiziranimi varnostnimi testi API-jev (npr. preizkusi poskusov neavtoriziranega dostopa s kodo 401/403) ter uvedba celostnih E2E testov uporabniškega vmesnika z orodjem Playwright.
3. **Merjenje pokritosti kode:** Vzpostavitev orodja `pytest-cov` za natančno spremljanje pokritosti kode s testi znotraj GitHub Actions cevovoda.

---

## 7. Izjava o uporabi generativnih orodij umetne inteligence

V skladu z navodili za oddajo naloge izjavljava, da je bil pri izdelavi tega poročila uporabljen agent **Gemini 3.8 Flash High**.

Orodje je bilo uporabljeno za analizo in pripravo začetnega osnutka poročila, ki pa je bilo nato podrobno pregledano, obdelano ter spreminjano s strani obeh članov ekipe (Tilen Kek in Mihajlo Dejanović).

