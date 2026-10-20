# Poročilo o testiranju enot, presoji kakovosti testov in integraciji v CI/CD cevovod

**Predmet:** Zagotavljanje kakovosti  
**Projekt:** NIDiKo – Priporočilni sistem za izbiro učnih poti (Praktikum II)  
**Avtorja poročila:** Tilen Kek, Mihajlo Dejanović  
**Datum izdelave:** Oktober 2026  
**Povezano poročilo:** `docs/Porocilo_Testiranje_Enot_NIDiKo.pdf` / `docs/Porocilo_Testiranje_Enot_NIDiKo.docx`

---

## Kazalo vsebine
1. Uvod in izhodiščno stanje testiranja v projektu NIDiKo](#1-uvod-in-izhodiščno-stanje-testiranja-v-projektu-nidiko)
2. Izbira treh enot z netrivialno logiko in specifikacija delovanja](#2-izbira-treh-enot-z-netrivialno-logiko-in-specifikacija-delovanja)
   - 2.1 Enota 1: Ocenjevalni servis (AssessmentService)](#21-enota-1-ocenjevalni-servis-assessmentservice)
   - 2.2 Enota 2: Servis za pripravo vprašalnikov (QuestionnaireService)](#22-enota-2-servis-za-pripravo-vprašalnikov-questionnaireservice)
   - 2.3 Enota 3: Iskalni servis (SearchService)](#23-enota-3-iskalni-servis-searchservice)
3. Ustvarjanje testov enot z AI agentom (Prompt Engineering)](#3-ustvarjanje-testov-enot-z-ai-agentom-prompt-engineering)
4. Preverjanje zanesljivosti testov z namernim vnosom napak (Mutacijsko testiranje)](#4-preverjanje-zanesljivosti-testov-z-namernim-vnosom-napak-mutacijsko-testiranje)
   - 4.1 Pregledna matrika vseh 6 vnesenih napak in odziv testov](#41-pregledna-matrika-vseh-6-vnesenih-napak-in-odziv-testov)
   - 4.2 Podrobna analiza napak v AssessmentService](#42-podrobna-analiza-napak-v-assessmentservice)
   - 4.3 Podrobna analiza napak v QuestionnaireService](#43-podrobna-analiza-napak-v-questionnaireservice)
   - 4.4 Podrobna analiza napak v SearchService](#44-podrobna-analiza-napak-v-searchservice)
5. Iskanje, analiza in popravek pomanjkljivih testov](#5-iskanje-analiza-in-popravek-pomanjkljivih-testov)
   - 5.1 Identifikacija opuščene prazne testne datoteke (tests/test_main.py)](#51-identifikacija-opuščene-prazne-testne-datoteke-teststest_mainpy)
   - 5.2 Izvedena implementacija testov za app/main.py](#52-izvedena-implementacija-testov-za-appmainpy)
6. Integracija v CI/CD cevovod in poročilo o pokritosti](#6-integracija-v-cicd-cevovod-in-poročilo-o-pokritosti)
   - 6.1 Posodobitev GitHub Actions delotoka (.github/workflows/ci.yml)](#61-posodobitev-github-actions-delotoka-githubworkflowsciyml)
   - 6.2 Mehanizem ustavitve cevovoda ob neuspelem testu](#62-mehanizem-ustavitve-cevovoda-ob-neuspelem-testu)
   - 6.3 Poročilo o pokritosti kode (Coverage Report)](#63-poročilo-o-pokritosti-kode-coverage-report)
7. Popoln popis vseh 43 testnih modulov v projektu (634 testov)](#7-popoln-popis-vseh-43-testnih-modulov-v-projektu-634-testov)
8. Sklepne ugotovitve in izjava o orodjih UI](#8-sklepne-ugotovitve-in-izjava-o-orodjih-ui)

---

## 1. Uvod in izhodiščno stanje testiranja v projektu NIDiKo

V okviru vaj pri predmetu **Zagotavljanje kakovosti** nadaljujemo analizo in nadgradnjo sistema **NIDiKo**, razvitega pri predmetu Praktikum II. Enotsko testiranje (angl. *Unit Testing*) je ključen in nepogrešljiv mehanizem zagotavljanja pravilnosti programske kode. Namen enotskega testiranja je izolirana validacija posameznih komponent programske opreme, funkcij, razredov in servisov, preden se ti povežejo v kompleksnejše integracijske celote.

Aplikacija NIDiKo povezuje sodobne spletne tehnologije:
- **FastAPI** zaledje (Python 3.13), organizirano v večplastno arhitekturo (API usmerjevalniki, domenske sheme, servisi poslovne logike, repozitoriji ter podatkovni sloj),
- **MongoDB Atlas** kot dokumentno podatkovno bazo,
- **Supabase Auth** za varno avtentikacijo s tokeni JWT,
- **Microsoft Azure** kognitivne storitve (Azure OpenAI in Azure Speech SDK) za podporo inteligentnim asistentom in glasovnemu vprašalniku,
- **React / TypeScript odjemalec** s prilagojenim uporabniškim vmesnikom.

> !NOTE]
> **Izhodiščna ugotovitev:** Pred začetkom te naloge je zaledje že vsebovalo obsežno zbirko **629 avtomatiziranih testov** v 42 datotekah. Vendar pa je pregled razkril opuščeno prazno datoteko `backend/tests/test_main.py` (0 bajtov), CI cevovod pa ni meril pokritosti kode s testi niti ni generiral trajnih poročil o pokritosti. V sklopu te naloge smo vse pomanjkljivosti odpravili, skupno število delujočih testov dvignili na **634**, izvedli mutacijsko testiranje nad 3 netrivialnimi enotami ter v celoti nadgradili CI cevovod.

---

## 2. Izbira treh enot z netrivialno logiko in specifikacija delovanja

V projektu smo izbrali tri enote z visoko stopnjo kompleksnosti, kjer napačna logika neposredno vpliva na pravilnost delovanja priporočilnega sistema, uporabniško izkušnjo ali celovitost podatkov:

### 2.1 Enota 1: Ocenjevalni servis (`AssessmentService`)
- **Datoteka implementacije:** `backend/app/services/assessments/assessment_service.py`
- **Datoteka testov:** `backend/tests/services/test_assessment_service.py` (36 testov)
- **Obseg kode:** 908 vrstic | **Pokritost kode:** 95 %

#### Utemeljitev izbire
`AssessmentService` je osrednji priporočilni agregator platforme NIDiKo. Sprejema uporabnikove odgovore samoocene (DA/NE), preračunava usvojenost posameznih tem (`content_topics`), združuje kompetenčne kode ter z večpogojno logiko določa, ali je uporabnik učno vsebino opravil (`PASSED`), delno obvlada (`PARTIAL`) ali pa jo mora začeti znova (`FAILED`). Prav tako določa priporočeno začetno točko (`start_module_id` in `start_learning_unit_id`). Napačna logika bi uporabniku predlagala napačno učno snov ali ga po krivem obravnavala kot neuspešnega.

#### Specifikacija pričakovanega delovanja
1. **Vhodni podatki:** `user_id` (niz), `target_type` (`QuestionnaireTargetType`: učna pot, modul ali učna enota), `target_id` (niz) in seznam odgovorov `answers` z objekti `{"question_id": str, "question": str, "answer": bool}`.
2. **Normalizacija vprašanj (`_normalize_question_text`):** Besedilo vprašanja mora pretvoriti v male črke, odstraniti robne presledke ter zaporedne presledke zmanjšati na enojne. Če vprašanje ni niz (npr. `None`), mora vrniti prazen niz `""`.
3. **Preslikava odgovorov (`_build_answer_maps`):** Izgradi dva iskalna indeksa: po `question_id` in po normaliziranem besedilu `question_text`. To omogoča, da en sam odgovor uporabnika zadošča za več enot, ki si delijo enako vprašanje.
4. **Prednostno iskanje odgovora (`_get_answer_for_question`):** Najprej preveri prisotnost po `question_id`. Če ID ne obstaja v slovarju, se zanaša na normalizirano besedilo. Če odgovora ni, vrne `None`.
5. **Izračun napredka (`_calculate_question_progress`):** Razmerje med številom znanih vprašanj in vsemi vprašanji. Če je skupno število $\le 0$, vrne `0.0`. Rezultat mora biti strogo omejen na interval $[0.0, 1.0]$.
6. **Izhodni rezultat:** Strukturiran slovar z identifikatorji, skupnim statusom, odstotkom usvojenosti, seznami opravljenih in priporočenih modulov/enot ter manjkajočimi kompetencami.

---

### 2.2 Enota 2: Servis za pripravo vprašalnikov (`QuestionnaireService`)
- **Datoteka implementacije:** `backend/app/services/questionnaires/questionnaire_service.py`
- **Datoteka testov:** `backend/tests/services/test_questionnaire_service.py` (30 testov)
- **Obseg kode:** 544 vrstic | **Pokritost kode:** 92 %

#### Utemeljitev izbire
`QuestionnaireService` dinamično gradi vprašalnike s hierarhičnim prečesavanjem strukture učnih poti in modulov. Vsebuje kompleksno logiko deduplikacije: če se v več učnih enotah pojavi identično vprašanje, ga uporabniku prikaže natanko enkrat, hkrati pa ohrani in združi vse relacijske vire (`sources`) za zaledno analizo kompetenc.

#### Specifikacija pričakovanega delovanja
1. **Preverjanje obstoja vsebine:** Asinhrono preveri obstoj učne poti, modula ali učne enote prek ustreznih podrejenih servisov. Če entiteta ne obstaja, vrne `None`.
2. **Hierarhična agregacija:** Iz vseh vključenih učnih enot izlušči polja `self_assessment_questions`.
3. **Validacija in normalizacija vprašanj (`_normalize_question`):** Vprašanja brez `id` ali brez besedila vprašanja (`question`) varno preskoči. Določi privzeti tip `YES_NO` in zgradi primarni vir `source`.
4. **Združevanje virov podvojenih vprašanj (`_merge_question_sources`):** Ob zaznavi enakega normaliziranega besedila vprašanja združi sezname `sources` brez izgube metapodatkov o pripadajočih modulih ali kompetencah.
5. **Izhodni format:** Vprašalnik s seznami unikatnih vprašanj, navigacijskimi metapodatki ter predpogoji.

---

### 2.3 Enota 3: Iskalni servis (`SearchService`)
- **Datoteka implementacije:** `backend/app/services/search/search_service.py`
- **Datoteka testov:** `backend/tests/services/test_search_service.py` (16 testov)
- **Obseg kode:** 170 vrstic | **Pokritost kode:** 100 %

#### Utemeljitev izbire
`SearchService` združuje iskalne poizvedbe čez tri ločene repozitorije (učne poti, moduli, učne enote). Njegova logika je netrivialna predvsem z vidika defenzivnega programiranja in tipskega čiščenja nehomogenih dokumentov MongoDB, kjer polja ključnih besed pogosto vsebujejo neveljavne vrednosti (`None`, števila ali prazne nize), ki bi brez filtriranja porušili Pydantic validacijo odgovora.

#### Specifikacija pričakovanega delovanja
1. **Sanitizacija seznamov nizov (`_get_string_list_value`):** Prejme surovo vrednost polja. Če vrednost ni seznam, vrne prazen seznam `]`. Iz seznama izloči vse elemente, ki niso nizi ali so prazni, veljavne nize pa očisti obrobnih presledkov (`strip()`).
2. **Varna preslikava entitet (`_to_search_result`):** Poskrbi za varno preslikavo polj: če manjkata `_id` ali `id`, varno izbere obstoječega; zagotovi veljavna polja `title`, `description`, `content_type` in `keywords`.
3. **Selektivno in privzeto iskanje (`search`):** Če parameter `types` ni podan (je `None`), privzeto išče po vseh treh tipih (`LEARNING_PATH`, `MODULE`, `LEARNING_UNIT`). Če je podan specifičen seznam tipov, poizveduje zgolj ustrezne repozitorije ter združi rezultate.

---

## 3. Ustvarjanje testov enot z AI agentom (Prompt Engineering)

Za generiranje enotskih testov s pomočjo UI agenta je bil pripravljen natančen ukaz, ki zagotavlja visoko raven pokritosti in konsistentnost s projektnimi standardi:

```text
UKAZ ZA AI AGENTA (PROMPT SPECIFIKACIJA):
================================================================================
Ustvari celovito zbirko enotskih testov v ogrodju Pytest za izbrano enoto poslovne logike.

Zahteve za teste:
1. Ogrodje in izvajanje:
   - Uporabi ogrodje Pytest (različica 9.0+) in razširitev pytest-asyncio (način auto).
   - Za izolacijo zunanjih odvisnosti (podatkovna baza MongoDB, sosednji servisi) uporabi
     nadomestne objekte (mock) z uporabo unittest.mock.AsyncMock ali namenskih Fake razredov.

2. Obseg pokritosti testnih scenarijev:
   - Običajni primeri (Happy path): uspešna obdelava veljavnih podatkov, standardni tokovi.
   - Robne vrednosti (Edge cases): prazni nizi, prazni seznami, mejni odstotki (0 %, 100 %),
     maksimalne vrednosti, vprašanja z enakim besedilom ali manjkajočimi identifikatorji.
   - Neveljavni vhodi (Invalid inputs): vrednosti None, neveljavni podatkovni tipi (npr. integer
     namesto stringa), manjkajoča obvezna polja v slovarjih.
   - Izjeme (Exception handling): pravilno proženje in prestrezanje HTTPException z ustreznimi
     statusnimi kodami (404 Not Found, 400 Bad Request) ter varno vračanje privzetih vrednosti.

3. Konvencija poimenovanja in struktura testov:
   - Ime vsake testne funkcije mora dosledno slediti vzorcu:
     test_<testirana_funkcija>_<testni_scenarij>_<pricakovani_rezultat>
   - Primer: test_get_answer_for_question_falls_back_to_question_text
   - Vsak test mora vsebovati strukturiran docstring ali pojasnjevalni komentar, ki pojasnjuje
     namen preverjanja ter jasne trditve (assert), ki preverjajo točne vrednosti in tipe.
================================================================================
```

### Ocena kakovosti generiranih testov
Generirani testi v celoti upoštevajo zastavljene zahteve:
- Vse zunanje odvisnosti so simulirane z `AsyncMock` ali lahkimi lažnimi objekti (`FakeCollection`, `FakeDatabase`), kar zagotavlja deterministično izvajanje brez potrebe po zunanji povezavi v MongoDB Atlas.
- Konvencija poimenovanja je dosledna in takoj razkriva namen testa.
- Testi preverjajo tako pozitivne kot negativne scenarije in robne vrednosti (npr. prazen vnos, neobstoječi ID, manjkajoči podatki).

---

## 4. Preverjanje zanesljivosti testov z namernim vnosom napak (Mutacijsko testiranje)

Da bi empirično dokazali, da testi niso zgolj pasivni opazovalci, ampak zanesljivo zaznajo programske hrošče, smo izvedli t.i. **mutacijsko testiranje**. V vsako od treh izbranih enot smo namerno vnesli **po dve logični napaki** (skupaj 6 napak).

### 4.1 Pregledna matrika vseh 6 vnesenih napak in odziv testov

| Enota | Oznaka napake | Opis vnesene napake v kodi | Odpovedali testi (FAILED) | Rezultat detekcije |
| :--- | :--- | :--- | :--- | :---: |
| **AssessmentService** | **Napaka 1A** | Opustitev pretvorbe v male črke in strnjenja več presledkov v `_normalize_question_text` | **4 testi** (`test_normalize_question_text_normalizes_text`, `test_build_answer_maps...`, `test_get_answer...`, `test_evaluate...`) | ✅ **100 % ZAZNANO** |
| **AssessmentService** | **Napaka 1B** | Onemogočitev iskanja odgovora po `question_id` v `_get_answer_for_question` (`if False:`) | **1 test** (`test_get_answer_for_question_prefers_question_id`) | ✅ **100 % ZAZNANO** |
| **QuestionnaireService** | **Napaka 2A** | Odsotnost normalizacije besedila vprašanja v `_normalize_question_text` (vračanje surovega niza) | **3 testi** (`test_normalize_question_text_normalizes_spaces_and_case`, `test_deduplicate...`, `test_normalize...`) | ✅ **100 % ZAZNANO** |
| **QuestionnaireService** | **Napaka 2B** | Opustitev združevanja virov v `_merge_question_sources` (`pass` namesto `extend`) | **3 testi** (`test_merge_question_sources_adds_duplicate_sources`, `test_deduplicate...`, `test_normalize...`) | ✅ **100 % ZAZNANO** |
| **SearchService** | **Napaka 3A** | Opustitev filtriranja `None` in ne-string elementov v `_get_string_list_value` | **2 testa** (`test_get_string_list_value_accepts_valid_string_list`, `test_to_search_result_uses_safe_fallback_values`) | ✅ **100 % ZAZNANO** |
| **SearchService** | **Napaka 3B** | Privzeto iskanje zgolj po učnih poteh namesto po vseh treh tipih vsebin v `search()` | **1 test** (`test_search_without_types_searches_all_content_types`) | ✅ **100 % ZAZNANO** |

---

### 4.2 Podrobna analiza napak v AssessmentService

#### Napaka 1A: Opustitev normalizacije besedila vprašanja
- **Sprememba v kodi (`backend/app/services/assessments/assessment_service.py`):**
  ```diff
  - return " ".join(question.strip().lower().split())
  + return question.strip()
  ```
- **Vpliv napake:** Vprašanja z različno velikimi začetnicami ali večkratnimi presledki niso bila več prepoznana kot identična.
- **Rezultat testiranja:** Testna zbirka je napako nemudoma zaznala s 4 odpovedmi testov (32 passed, 4 failed).
- **Izpis Pytest konzole:**
  ```text
  FAILED tests/services/test_assessment_service.py::test_normalize_question_text_normalizes_text
  E   AssertionError: assert 'Razumem   osnovne   pojme.' == 'razumem osnovne pojme.'
  E     - razumem osnovne pojme.
  E     + Razumem   osnovne   pojme.
  Exit code: 1
  ```

#### Napaka 1B: Onemogočitev iskanja po identifikatorju vprašanja
- **Sprememba v kodi (`backend/app/services/assessments/assessment_service.py`):**
  ```diff
  - if question_id in by_question_id:
  -     return by_question_id.get(question_id)
  + if False:
  +     return by_question_id.get(question_id)
  ```
- **Vpliv napake:** Servis je spregledal eksplicitno določen odgovor po ID-ju vprašanja ter se zanašal zgolj na besedilo vprašanja.
- **Rezultat testiranja:** 1 test je odpovedal (35 passed, 1 failed).
- **Izpis Pytest konzole:**
  ```text
  FAILED tests/services/test_assessment_service.py::test_get_answer_for_question_prefers_question_id
  E   AssertionError: assert False is True
  E    +  where False = <bound method AssessmentService._get_answer_for_question(...)>
  Exit code: 1
  ```

---

### 4.3 Podrobna analiza napak v QuestionnaireService

#### Napaka 2A: Odsotnost normalizacije vprašanj v vprašalniku
- **Sprememba v kodi (`backend/app/services/questionnaires/questionnaire_service.py`):**
  ```diff
  - return " ".join(question.strip().lower().split())
  + return question
  ```
- **Vpliv napake:** Deduplikacija je odpovedala, uporabniku bi se ista vprašanja z minimalnimi razlikami v presledkih podvajala.
- **Rezultat testiranja:** 3 testi so odpovedali (27 passed, 3 failed).
- **Izpis Pytest konzole:**
  ```text
  FAILED tests/services/test_questionnaire_service.py::test_normalize_question_text_normalizes_spaces_and_case
  E   AssertionError: assert '  Znam uporabljati Excel.  ' == 'znam uporabljati excel.'
  Exit code: 1
  ```

#### Napaka 2B: Opustitev združevanja virov pri podvojenih vprašanjih
- **Sprememba v kodi (`backend/app/services/questionnaires/questionnaire_service.py`):**
  ```diff
  - existing_sources.extend(duplicate_sources)
  + pass
  ```
- **Vpliv napake:** Pri deduplikaciji so se izgubili vsi sekundarni viri vprašanja, kar bi v priporočilnem algoritmu povzročilo izgubo povezav do povezanih kompetenc.
- **Rezultat testiranja:** 3 testi so odpovedali (27 passed, 3 failed).
- **Izpis Pytest konzole:**
  ```text
  FAILED tests/services/test_questionnaire_service.py::test_merge_question_sources_adds_duplicate_sources
  E   AssertionError: assert len(result'sources']) == 2
  E    +  where len(result'sources']) = 1
  Exit code: 1
  ```

---

### 4.4 Podrobna analiza napak v SearchService

#### Napaka 3A: Opustitev filtriranja neveljavnih elementov v ključnih besedah
- **Sprememba v kodi (`backend/app/services/search/search_service.py`):**
  ```diff
  - return item.strip() for item in value if isinstance(item, str) and item.strip()]
  + return value if isinstance(value, list) else ]
  ```
- **Vpliv napake:** V seznamih ključnih besed so ostale vrednosti `None`, števila in prazni nizi, kar krši Pydantic shemo `SearchResponse`.
- **Rezultat testiranja:** 2 testa sta odpovedala (14 passed, 2 failed).
- **Izpis Pytest konzole:**
  ```text
  FAILED tests/services/test_search_service.py::test_get_string_list_value_accepts_valid_string_list
  E   AssertionError: assert None, 123, 'Excel', ''] == 'Excel']
  Exit code: 1
  ```

#### Napaka 3B: Zoženje privzetega iskanja na zgolj en tip vsebine
- **Sprememba v kodi (`backend/app/services/search/search_service.py`):**
  ```diff
  - selected_types = types or SearchContentType.LEARNING_PATH, SearchContentType.MODULE, SearchContentType.LEARNING_UNIT]
  + selected_types = types or SearchContentType.LEARNING_PATH]
  ```
- **Vpliv napake:** Iskalnik brez eksplicitno izbranih tipov ni več poizvedoval po modulih in učnih enotah.
- **Rezultat testiranja:** 1 test je odpovedal (15 passed, 1 failed).
- **Izpis Pytest konzole:**
  ```text
  FAILED tests/services/test_search_service.py::test_search_without_types_searches_all_content_types
  E   AssertionError: assert len(result) == 3
  E    +  where len(result) = 1
  Exit code: 1
  ```

---

## 5. Iskanje, analiza in popravek pomanjkljivih testov

### 5.1 Identifikacija opuščene prazne testne datoteke (`tests/test_main.py`)
Pri pregledu celotne testne zbirke z orodjem AST (Abstract Syntax Tree) in primerjavi s collected items orodja Pytest smo ugotovili, da se v mapi `backend/tests/` nahaja datoteka:
```text
backend/tests/test_main.py (velikost: 0 bajtov)
```
Ta datoteka je bila ob začetni postavitvi repozitorija predvidena za testiranje vstopne točke `app/main.py`, vendar je ostala popolnoma prazna. Posledično korenski endpoint, inicializacija CORS pravilnikov ter registracija usmerjevalnikov niso bili pokriti z avtomatskimi testi.

### 5.2 Izvedena implementacija testov za `app/main.py`
Datoteko `backend/tests/test_main.py` smo v celoti na novo implementirali s 5 zanesljivimi testi:

1. `test_read_root_returns_200_and_message`: preveri korenski klic `GET /` in potrdi status 200 ter odziv `{"message": "NIDiKo backend is running."}`.
2. `test_app_metadata`: preveri metapodatke aplikacije FastAPI (`app.title == "NIDiKo API"`, `app.version == "0.1.0"`).
3. `test_cors_middleware_allows_configured_origins`: simulira HTTP `OPTIONS /` zahtevek z dovoljenim izvorom `http://localhost:5173` in preveri prisotnost glav `access-control-allow-origin` ter `access-control-allow-credentials`.
4. `test_registered_api_routes`: preveri, da so vsi domenski usmerjevalniki (`/api/search`, `/api/learning-paths`, `/api/modules`, `/api/learning-units`, `/api/users`, `/api/user-progress`) registrirani v aplikacijskem objektu.
5. `test_not_found_returns_404`: preveri, da klic neobstoječega naslova pravilno vrne HTTP status 404.

Zagon testov:
```bash
pytest tests/test_main.py -v
```
Vseh 5 testov je uspešno prestalo preverjanje, s čimer se je skupno število testov v zaledju povečalo na **634**.

---

## 6. Integracija v CI/CD cevovod in poročilo o pokritosti

### 6.1 Posodobitev GitHub Actions delotoka (`.github/workflows/ci.yml`)
V skladu z zahtevo:
> *"Teste enot vključite v ustvarjen cevovod tako, da neuspešen test ustavi izvajanje cevovoda. Poročilo o pokritosti naj bo del rezultatov cevovoda"*

smo izvedli naslednje spremembe:
1. V `backend/requirements.txt` smo dodali orodje `pytest-cov==7.1.0`.
2. V delotoku `.github/workflows/ci.yml` smo posodobili opravilo `backend-tests`:

```yaml
  backend-tests:
    name: Backend tests with coverage
    runs-on: ubuntu-latest
    needs: backend-build

    defaults:
      run:
        working-directory: backend

    env:
      PYTHONPATH: .
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

    steps:
      - name: Checkout repository
        uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Install backend dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt

      - name: Run backend tests with coverage
        run: |
          python -m pytest --asyncio-mode=auto --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov

      - name: Generate Coverage Step Summary
        if: always()
        run: |
          echo "### 📊 Python Test Coverage Summary" >> $GITHUB_STEP_SUMMARY
          python -m coverage report --format=markdown >> $GITHUB_STEP_SUMMARY || true

      - name: Upload coverage report artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage-report
          path: |
            backend/coverage.xml
            backend/htmlcov
          retention-days: 14
```

### 6.2 Mehanizem ustavitve cevovoda ob neuspelem testu
Če katerikoli test odpove, orodje Pytest vrne kodo `1`. Ker v GitHub Actions korak teče brez zastavice `continue-on-error: true`, se opravilo `backend-tests` nemudoma prekine s statusom **FAILED**. V delotoku `staging-deploy.yml` je opravilo postavitve na strežnik pogojeno z `needs: ci`, kar pomeni, da je kakršnakoli namestitev kode z napako na strežnik popolnoma onemogočena.

### 6.3 Poročilo o pokritosti kode (Coverage Report)
Zagon orodja `pytest-cov` nad zaledjem je ustvaril interaktivno poročilo `htmlcov/` in XML obliko `coverage.xml`.

#### Povzetek pokritosti ključnih komponent:
| Modul / Servis zaledja | Število vrstic | Izpuščene vrstice | Pokritost (%) |
| :--- | :---: | :---: | :---: |
| `app/services/search/search_service.py` | 36 | 0 | **100 %** |
| `app/services/users/user_service.py` | 21 | 0 | **100 %** |
| `app/services/user_progress/user_progress_service.py` | 10 | 0 | **100 %** |
| `app/main.py` | 38 | 0 | **100 %** |
| `app/database/mongodb.py` | 6 | 0 | **100 %** |
| `app/services/learning_units/learning_unit_service.py` | 132 | 2 | **98 %** |
| `app/services/modules/module_service.py` | 104 | 2 | **98 %** |
| `app/services/assessments/assessment_service.py` | 295 | 15 | **95 %** |
| `app/services/questionnaires/questionnaire_service.py` | 142 | 12 | **92 %** |
| `app/services/learning_paths/learning_path_service.py` | 142 | 14 | **90 %** |
| **Vsi jedrni servisi in repozitoriji** | **2.643** | **—** | **~94 %** |

---

## 7. Popoln popis vseh 43 testnih modulov v projektu (634 testov)

V spodnji tabeli podajamo celovit seznam vseh 43 testnih datotek po arhitekturnih slojih:

| Testna datoteka | Arhitekturni sloj | Št. testov | Status izvajanja |
| :--- | :--- | :---: | :---: |
| `tests/test_main.py` | Core / Vstopna točka aplikacije | 5 | ✅ Uspešno (Dopolnjeno) |
| `tests/api/test_assessments_api.py` | API usmerjevalniki (REST) | 9 | ✅ Uspešno |
| `tests/api/test_learning_paths_api.py` | API usmerjevalniki (REST) | 13 | ✅ Uspešno |
| `tests/api/test_learning_units_api.py` | API usmerjevalniki (REST) | 7 | ✅ Uspešno |
| `tests/api/test_modules_api.py` | API usmerjevalniki (REST) | 10 | ✅ Uspešno |
| `tests/api/test_questionnaires_api.py` | API usmerjevalniki (REST) | 8 | ✅ Uspešno |
| `tests/api/test_search_api.py` | API usmerjevalniki (REST) | 17 | ✅ Uspešno |
| `tests/api/test_user_progress_api.py` | API usmerjevalniki (REST) | 15 | ✅ Uspešno |
| `tests/api/test_users_api.py` | API usmerjevalniki (REST) | 12 | ✅ Uspešno |
| `tests/data/test_learning_paths_json.py` | Podatkovni šifranti in struktura | 15 | ✅ Uspešno |
| `tests/data/test_learning_units_json.py` | Podatkovni šifranti in struktura | 21 | ✅ Uspešno |
| `tests/data/test_modules_json.py` | Podatkovni šifranti in struktura | 16 | ✅ Uspešno |
| `tests/data/test_users_json.py` | Podatkovni šifranti in struktura | 18 | ✅ Uspešno |
| `tests/repositories/test_completed_content_repository.py` | Repozitoriji (MongoDB) | 8 | ✅ Uspešno |
| `tests/repositories/test_current_position_repository.py` | Repozitoriji (MongoDB) | 8 | ✅ Uspešno |
| `tests/repositories/test_learning_path_repository.py` | Repozitoriji (MongoDB) | 19 | ✅ Uspešno |
| `tests/repositories/test_learning_unit_repository.py` | Repozitoriji (MongoDB) | 16 | ✅ Uspešno |
| `tests/repositories/test_module_repository.py` | Repozitoriji (MongoDB) | 26 | ✅ Uspešno |
| `tests/repositories/test_questionnaire_answers_repository.py` | Repozitoriji (MongoDB) | 8 | ✅ Uspešno |
| `tests/repositories/test_user_progress_repository.py` | Repozitoriji (MongoDB) | 10 | ✅ Uspešno |
| `tests/repositories/test_user_repository.py` | Repozitoriji (MongoDB) | 14 | ✅ Uspešno |
| `tests/schemas/test_assessment_schema.py` | Pydantic domenske sheme | 18 | ✅ Uspešno |
| `tests/schemas/test_learning_path_schema.py` | Pydantic domenske sheme | 14 | ✅ Uspešno |
| `tests/schemas/test_learning_unit_schema.py` | Pydantic domenske sheme | 24 | ✅ Uspešno |
| `tests/schemas/test_module_schema.py` | Pydantic domenske sheme | 16 | ✅ Uspešno |
| `tests/schemas/test_questionnaire_schema.py` | Pydantic domenske sheme | 25 | ✅ Uspešno |
| `tests/schemas/test_search_schema.py` | Pydantic domenske sheme | 22 | ✅ Uspešno |
| `tests/schemas/test_user_progress_schema.py` | Pydantic domenske sheme | 35 | ✅ Uspešno |
| `tests/schemas/test_user_schema.py` | Pydantic domenske sheme | 33 | ✅ Uspešno |
| `tests/services/test_assessment_progress_service.py` | Servisi poslovne logike | 7 | ✅ Uspešno |
| `tests/services/test_assessment_service.py` | Servisi poslovne logike | 36 | ✅ Uspešno |
| `tests/services/test_learning_path_service.py` | Servisi poslovne logike | 16 | ✅ Uspešno |
| `tests/services/test_learning_unit_service.py` | Servisi poslovne logike | 26 | ✅ Uspešno |
| `tests/services/test_module_service.py` | Servisi poslovne logike | 16 | ✅ Uspešno |
| `tests/services/test_questionnaire_answers_prefill_service.py` | Servisi poslovne logike | 4 | ✅ Uspešno |
| `tests/services/test_questionnaire_prefill_service.py` | Servisi poslovne logike | 3 | ✅ Uspešno |
| `tests/services/test_questionnaire_service.py` | Servisi poslovne logike | 30 | ✅ Uspešno |
| `tests/services/test_search_service.py` | Servisi poslovne logike | 16 | ✅ Uspešno |
| `tests/services/test_user_progress_service.py` | Servisi poslovne logike | 5 | ✅ Uspešno |
| `tests/services/test_user_service.py` | Servisi poslovne logike | 13 | ✅ Uspešno |
| **SKUPAJ V REPOZITORIJU** | **43 testnih modulov** | **634** | **✅ 100 % Uspešno (3,54 s)** |

---

## 8. Sklepne ugotovitve in izjava o orodjih UI

### Sklep
Z izvedbo te naloge smo v projektu NIDiKo dosegli visoko stopnjo zanesljivosti in kakovosti programske opreme:
1. **Analiza in specifikacija:** Izbrali in specificirali smo tri najbolj kompleksne enote zaledja (`AssessmentService`, `QuestionnaireService`, `SearchService`).
2. **Empirična verifikacija:** Z mutacijskim testiranjem (6 vnesenih napak) smo dokazali **100 % stopnjo detekcije napak**, kar potrjuje, da testi niso le formalni, temveč aktivno varujejo poslovno logiko.
3. **Sanacija vrzeli:** Odpravili smo opuščeno prazno datoteko `test_main.py` ter implementirali 5 novih testov, s čimer celotna zbirka šteje **634 testov**.
4. **CI/CD avtomatizacija:** Vpeljali smo orodje `pytest-cov`, nastavili zaustavitev cevovoda ob napaki ter omogočili shranjevanje poročil o pokritosti kot artefaktov in povzetkov GitHub delotoka.

### Izjava o uporabi generativnih orodij umetne inteligence
Pri analizi kode, pripravi testnih matrik ter strukturiranju poročila so bila uporabljena orodja umetne inteligence (Claude, ChatGPT, Antigravity AI). Vsi generirani testi, skripte in popravki so bili ročno pregledani, strokovno verificirani z lokalnim zagonom `pytest` ter potrjeni v delotoku neprekinjene integracije.
