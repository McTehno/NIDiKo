# Načrt stresnega testiranja NIDiKo

**Status: načrt in testni sklop pripravljena (3. 11. 2026).** Čaka na uskladitev termina in potrditev razpoložljivosti staging strežnika z odgovornim za infrastrukturo. Test se ne sme izvajati sočasno z vzdržljivostnim testom ali običajnimi CI/CD namestitvami.

---

## 1. Namen, cilji in razlika z vzdržljivostnim testom

Medtem ko vzdržljivostni test (član Tilen) preverja **stabilnost in odsotnost degradacije ob stalni obremenitvi (100 uporabnikov skozi 8 ur)**, stresni test odgovarja na vprašanja zmogljivosti in meja obremenitve:

1. **Vedenje ob naraščanju obremenitve:** Kako se spreminjajo odzivni časi (p50, p95, p99, maksimum) in delež napak ob postopnem povečevanju števila aktivnih uporabnikov od 20 do 220?
2. **Točka preloma (bottleneck):** Pri kateri stopnji se pojavijo prvi znaki preobremenitve (nasičenje CPU, izčrpanje pomnilnika, zavračanje povezav ali zakasnitve)?
3. **Izvor ozkih grl:** Ali težave izvirajo iz spletnega strežnika (Uvicorn/FastAPI), podatkovne baze (MongoDB), zunanjih Azure storitev (Azure OpenAI, Speech) ali generatorja obremenitve?
4. **Zmožnost okrevanja (recovery):** Ali si sistem po zmanjšanju obremenitve nazaj na 20 mest opomore na raven začetne primerljive stopnje (Stage 1), ali pa ostane v degradiranem stanju?

> [!IMPORTANT]
> Če sistem do zadnje načrtovane stopnje (220 mest) ne odpove ali ne doseže zasičenja, se poroča, da meja zmogljivosti ni bila dosežena. Najvišja preizkušena stopnja ni nujno končna meja sistema.

---

## 2. Okolje in izhodiščna postavitev

Testiranje se izvaja proti javnemu naslovu staging okolja z ločenega računalnika (generatorja), da se prepreči tekmovanje za vire.

| Parameter | Vrednost / Opis |
|---|---|
| **Ciljni sistem** | Hetzner VPS CX23 (2 vCPU, ~4 GB RAM) |
| **Aplikacija** | Docker vsebnik (`nidiko_backend`), en proces Uvicorn, FastAPI |
| **Podatkovna baza** | Namenska začasna testna baza (MongoDB): `psi_up_staging_perf_stress_<TIMESTAMP>` |
| **Zunanje storitve** | Azure OpenAI (gpt-4o-mini), Azure AI Speech (sl-SI-PetraNeural), Azure Blob Storage |
| **Generator obremenitve** | Ločen zunanji računalnik, orodje Locust 2.47.0 (en proces, brez spanja) |
| **Učna pot** | `up_001` (14 vprašanj DA/NE) |
| **Testni profil** | `tests/performance/profiles/stress.json` |

---

## 3. Uporabniški model in porazdelitev vlog

Da so rezultati neposredno primerljivi z vzdržljivostnim testom, uporabniški potek ohranja popolnoma enak scenarij:
- Vsako aktivno mesto rešuje vprašalnik učne poti `up_001`.
- Po oddaji vseh odgovorov mesto začne nov potek z novim sintetičnim profilom iz evidence (`pool.json`).
- **40 % aktivnih mest** uporablja besedilnega AI pomočnika (pošlje 1–20 sporočil, uteženo povprečje 4,06 sporočila).
- **5 % aktivnih mest** uporablja glasovno pomoč (natanko enkrat na reševanje, podmnožica uporabnikov AI).
- **Premori:** 15–35 s za branje vprašanja; dodatnih 10–25 s po prejemu pomoči.
- Odgovori se zbirajo lokalno in se na koncu oddajo v eni zahtevi (`POST /api/assessments/evaluate`).

### Dinamično ohranjanje deležev (`SlotManager`)
Ker Locust ob zmanjševanju obremenitve (npr. prehod z 220 na 20 mest pri okrevanju) naključno ugaša uporabniške instance, stresni test uporablja komponento `SlotManager`. Ta vzdržuje urejen seznam aktivnih mest. Vsako mesto pred začetkom reševanja preveri svoj trenutni indeks med aktivnimi mesti (`rank`):
- `rank % 20 == 0`: Glasovni uporabnik (5 %)
- `rank % 20 < 8`: AI uporabnik (40 %)
- `rank % 20 >= 8`: Običajni uporabnik (60 %)

To zagotavlja matematično točne deleže pri vseh stopnjah (večkratniki 20), vključno s stopnjo okrevanja.

---

## 4. Načrtovani profil obremenitve (stopnje)

Predvideno skupno trajanje je približno **90 minut** (5.440 s), v kolikor se test ne ustavi predčasno zaradi kriterijev preobremenitve. Hitrost dodajanja uporabnikov je **2 uporabnika/s**.

| Faza / Stopnja | Aktivna mesta | Trajanje stabilne faze | Čas prehoda (ramp) | Namen faze |
|---|---:|---:|---:|---|
| **Ogrevanje (warmup)** | 20 | 5 min (300 s) | ~10 s | Inicializacija povezav in ogrevanje predpomnilnikov |
| **Stopnja 1** | 20 | 10 min (600 s) | 0 s | Izhodiščna primerjalna stopnja (baseline) |
| **Stopnja 2** | 40 | 10 min (600 s) | ~10 s | 2× začetna obremenitev |
| **Stopnja 3** | 60 | 10 min (600 s) | ~10 s | 3× začetna obremenitev |
| **Stopnja 4** | 100 | 10 min (600 s) | ~20 s | Primerjava z vzdržljivostnim testom (100 mest) |
| **Stopnja 5** | 140 | 10 min (600 s) | ~20 s | Preseganje vzdržljivostne obremenitve (+40 %) |
| **Stopnja 6** | 180 | 10 min (600 s) | ~20 s | Visoka obremenitev (+80 %) |
| **Stopnja 7** | 220 | 10 min (600 s) | ~20 s | Najvišja načrtovana obremenitev (120 % nad vzdržljivostnim) |
| **Okrevanje (recovery)** | 20 | 10 min (600 s) | ~100 s | Zmanjšanje na 20 mest in merjenje povrnitve odzivnosti |
| **Opazovanje (cooldown)** | 0 | 2 min (120 s) | ~10 s | Brez prometa, opazovanje sprostitve virov |

---

## 5. Kriteriji kakovosti in pogoji za predčasno ustavitev

### A. Kriteriji kakovosti storitve (SLA / ciljne meje)
- **Uspešnost zahtev:** $\ge 99{,}9\ \%$ uspešnih odgovorov HTTP 200 v vsaki skupini.
- **Običajni API-ji** (`GET /api/questionnaires`, `POST /api/assessments/evaluate`): vsaj $99\ \%$ zahtev z odzivom $\le 400\text{ ms}$.
- **Besedilni AI pomočnik** (`POST /api/assessment-assistant/message`): vsi odzivi $\le 7.000\text{ ms}$ (7 sekund).
- **Glasovna pomoč** (`POST /api/voice-help/question` in prenos zvoka):
  - API klic (iz predpomnilnika): $\le 3.000\text{ ms}$.
  - Prenos celotnega zvoka: $\le 3.000\text{ ms}$.

> [!NOTE]
> Preseganje časovnih kriterijev (npr. p99 > 400 ms) je **meritev degradacije**, ne pa razlog za prekinitev testa! Test se nadaljuje skozi stopnje, dokler sistem tehnično zdrži.

### B. Operativni pogoji za samodejni prehod v okrevanje (Overload Protection)
Komponenta `OverloadMonitor` sproti spremlja drseča 1-minutna okna (z vsaj 20 zahtevami). V okrevanje (20 mest) preide samodejno v primeru:
1. **Kritični skok napak:** Delež neuspešnih zahtev preseže **$10\ \%$ v enem 1-minutnem oknu**.
2. **Vztrajna preobremenitev:** Delež napak preseže **$5\ \%$ v dveh zaporednih 1-minutnih oknih**.
3. **Izpad ali sesutje:** Ponovni zagon backenda, OOM (Out Of Memory) ali nedosegljivost strežnika.
4. **Izčrpanje virov gostitelja:** Prosti RAM gostitelja pade pod $10\ \%$ za več kot minuto ali prosti disk pade pod $1\text{ GB}$.
5. **Azure 429 (Rate Limit):** Ob ponavljajočih se odgovorih 429 se zabeležijo kvote, prepreči agresivno ponavljanje in preide v okrevanje.
6. **Zasičenje generatorja:** Če CPU generatorja preseže $95\ \%$, se zabeleži omejitev generatorja.

---

## 6. Protokol izvedbe in obnova okolja

### Pred zagonom:
1. **Preveri status:** Potrdi z odgovornim za infrastrukturo, da je vzdržljivostni test zaključen in okolje prosto.
2. **Premor CI/CD:** Nastavi `STAGING_DEPLOY_PAUSED=true` v GitHub repozitoriju, da se preprečijo nepričakovane namestitve med meritvijo.
3. **Izolacija baze podatkov:**
   - Ustvari namensko bazo: `psi_up_staging_perf_stress_<TIMESTAMP>`.
   - Vstavi sintetične profile z orodjem `prepare_test_data.py` (priporočeno 3.500 do 5.000 profilov).
   - Preusmeri staging vsebnik na testno bazo.
   - **Prvotna baza `psi_up` s 29 obstoječimi profili se ne sme spreminjati ali brisati!**
4. **Kratek pilot:** Zaženi mini-pilot (20 mest, 2 minuti), da preveriš delovanje API-jev in beleženje dogodkov.
5. **Zagon infrastrukturnih meritev:** Na strežniku zaženi `bash tests/performance/scripts/collect_metrics.sh`.

### Med zagonom:
```powershell
# Predogled načrta in ocene klicev (brez pošiljanja zahtev)
python tests/performance/scripts/run_stress.py --data test-results/performance/stress_pool.json --app-commit <DEJANSKI-COMMIT> --environment-note "CX23, 2 vCPU, 4GB RAM, Docker Uvicorn"

# Dejanski zagon (ko je termin potrjen)
python tests/performance/scripts/run_stress.py --data test-results/performance/stress_pool.json --app-commit <DEJANSKI-COMMIT> --environment-note "CX23, 2 vCPU, 4GB RAM, Docker Uvicorn" --execute
```

### Po zagonu (obnova okolja):
1. Ustavi zbiranje infrastrukturnih meritev na strežniku in prenesi datoteke v mapo zagona.
2. Preklopi staging nazaj na originalno bazo `psi_up` in ponovno zaženi backend.
3. Odstrani `STAGING_DEPLOY_PAUSED` spremenljivko v GitHub repozitoriju.
4. Po arhiviranju dokazov pobriši sintetične profile iz testne baze s `cleanup_test_data.py`.
5. Preveri dosegljivost aplikacije in delovanje za običajne uporabnike.

