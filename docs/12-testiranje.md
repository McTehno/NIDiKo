# Testiranje

Ta dokument opisuje način preverjanja delovanja aplikacije **NIDiKo**.

Specifikacije šestih funkcionalnih scenarijev, odgovorne osebe, dejanski rezultati,
odstopanja in navodila za ponovitev so v
[poročilu funkcionalnega testiranja](16-porocilo-funkcionalno-testiranje.md).
Dokazi ponovitve 29. 10. 2026 so ločeni od prvotnih dokazov z dne 27. 10. 2026.

Namen testiranja je zagotoviti, da frontend, backend, podatkovna baza, avtentikacija, vprašalnik, AI pomočnik in uporabniški napredek delujejo pravilno ter da spremembe ne pokvarijo obstoječih funkcionalnosti.

---

## 1. Namen testiranja

Testiranje v projektu NIDiKo vključuje:

- preverjanje zagona aplikacije,
- preverjanje frontend kode,
- preverjanje backend kode,
- preverjanje API povezav,
- ročno testiranje uporabniških tokov,
- preverjanje odzivnega prikaza,
- preverjanje avtentikacije,
- preverjanje uporabniškega napredka,
- preverjanje vprašalnika,
- preverjanje AI in glasovne pomoči.

Testiranje je pomembno predvsem zato, ker aplikacija povezuje več delov sistema: React frontend, FastAPI backend, MongoDB Atlas, Supabase Auth in Microsoft Azure storitve.

---

## 2. Preverjanje pred začetkom testiranja

Pred testiranjem preverimo, da so pripravljene okoljske spremenljivke:

```text
backend/.env
frontend/.env
```

Projekt lahko zaženemo z Docker Compose:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Po zagonu preverimo:

| Del aplikacije | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend API | `http://localhost:8000` |
| Swagger dokumentacija | `http://localhost:8000/docs` |

---

## 3. Frontend preverjanje

Frontend preverimo iz mape `frontend`.

```bash
cd frontend
npm install
npm run build
```

Build mora uspeti brez TypeScript napak.

Pri frontend preverjanju preverimo:

- aplikacija se zažene,
- strani se pravilno naložijo,
- ni TypeScript napak,
- ni očitnih napak v konzoli brskalnika,
- API klici delujejo prek `src/services`,
- ni direktnih `fetch` klicev v komponentah,
- tipi so usklajeni s podatki iz backenda,
- obstoječi izgled strani ni po nepotrebnem spremenjen.

Za razvojni zagon frontenda:

```bash
npm run dev
```

---

## 4. Backend preverjanje

Backend preverimo iz mape `backend`.

```bash
cd backend
python -m venv venv
```

Aktivacija virtualnega okolja na Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Namestitev odvisnosti:

```bash
pip install -r requirements.txt
```

Zagon backenda:

```bash
uvicorn app.main:app --reload
```

Backend preverimo na:

```text
http://localhost:8000/docs
```

Pri backend preverjanju preverimo:

- aplikacija se zažene brez napak,
- povezava z MongoDB deluje,
- Swagger dokumentacija se odpre,
- endpointi vračajo pričakovane podatke,
- napake so obravnavane z ustreznimi statusnimi kodami,
- zaščiteni endpointi preverjajo prijavljenega uporabnika,
- podatki v response oblikah ustrezajo frontend tipom.

Če so testi pripravljeni, jih zaženemo z:

```bash
pytest
```

---

## 5. Preverjanje API endpointov

API endpointi se lahko preverijo prek Swagger dokumentacije:

```text
http://localhost:8000/docs
```

Pri API testiranju preverimo glavne sklope:

- učne poti,
- module,
- učne enote,
- iskanje,
- vprašalnike,
- rezultate samoocene,
- uporabnike,
- uporabniški napredek,
- AI pomočnika in glasovno pomoč, kjer je to omogočeno.

Za vsak pomemben endpoint preverimo:

- ali endpoint vrne pričakovan odgovor,
- ali napačen ID vrne ustrezno napako,
- ali zaščiten endpoint zahteva prijavo,
- ali so podatki usklajeni s frontend prikazom.

---

## 6. Ročno testiranje uporabniških tokov

Ročno testiranje preverja, ali uporabnik lahko uspešno izvede glavne tokove aplikacije.

### 6.1 Neprijavljen uporabnik

Preverimo, da neprijavljen uporabnik lahko:

- odpre začetno stran,
- uporablja iskanje,
- odpre stran podrobnosti učne poti,
- odpre stran podrobnosti modula,
- odpre stran podrobnosti učne enote,
- reši vprašalnik,
- uporablja AI pomočnika,
- uporablja glasovno pomoč pri vprašalniku.

Preverimo tudi, da neprijavljen uporabnik ne more:

- shraniti vsebine,
- označiti vsebine kot priljubljene,
- označiti vsebine kot dokončane.

Če poskusi uporabiti zaščiteno funkcionalnost, mora biti preusmerjen k prijavi oziroma mora dobiti jasno sporočilo.

### 6.2 Prijavljen uporabnik

Preverimo, da prijavljen uporabnik lahko:

- uporablja vse funkcionalnosti neprijavljenega uporabnika,
- shrani učno pot, modul ali učno enoto,
- označi vsebino kot priljubljeno,
- označi vsebino kot dokončano,
- vidi posodobljen napredek,
- nadaljuje iz trenutne pozicije,
- ima shranjen rezultat vprašalnika.

---

## 7. Testiranje vprašalnika

Vprašalnik je eden ključnih tokov aplikacije.

Preverimo:

- vprašalnik se odpre za učno pot,
- vprašalnik se odpre za modul,
- vprašalnik se odpre za učno enoto,
- vprašanja so tipa DA/NE,
- uporabnik lahko odgovori na vprašanja,
- oddaja vprašalnika deluje,
- rezultat se pravilno prikaže,
- priporočena začetna točka je prikazana razumljivo,
- pri prijavljenem uporabniku se rezultat shrani v napredek.

Preverimo tudi robne primere:

- uporabnik odgovori z DA na vsa vprašanja,
- uporabnik odgovori z NE na vsa vprašanja,
- uporabnik odgovori mešano,
- uporabnik zapusti vprašalnik pred oddajo,
- uporabnik ponovno odpre vprašalnik.

---

## 8. Testiranje uporabniškega napredka

Pri uporabniškem napredku preverimo:

- shranjevanje vsebine,
- odstranitev iz shranjenih vsebin,
- označevanje kot priljubljeno,
- odstranitev iz priljubljenih,
- označevanje kot dokončano,
- odstranitev iz dokončanih,
- posodobitev trenutne pozicije,
- prikaz napredka na straneh podrobnosti.

Posebej preverimo, da uporabnik lahko dostopa samo do svojega napredka.

---

## 9. Testiranje AI pomočnika

AI pomočnik se preveri na:

- strani podrobnosti učne poti,
- strani podrobnosti modula,
- strani podrobnosti učne enote,
- vprašalniku.

Preverimo:

- AI pomočnik se prikaže,
- uporabnik lahko pošlje vprašanje,
- odgovor je povezan s trenutnim kontekstom,
- napaka pri AI storitvi je prikazana razumljivo,
- AI pomočnik ne pokvari osnovnega toka strani.

---

## 10. Testiranje glasovne pomoči

Glasovna pomoč se preveri pri vprašalniku.

Preverimo:

- glasovna pomoč se zažene,
- uporabnik prejme zvočno podporo,
- manjkajoče Azure nastavitve ne porušijo celotnega vprašalnika,
- napaka je uporabniku prikazana razumljivo,
- vprašalnik ostane uporaben tudi brez glasovne pomoči.

---

## 11. Preverjanje odzivnega prikaza

Aplikacijo preverimo na treh velikostih zaslona:

- namizni prikaz,
- tablični prikaz,
- mobilni prikaz.

Preverimo:

- začetno stran,
- iskanje,
- strani podrobnosti,
- vprašalnik,
- rezultat vprašalnika,
- prijavo in registracijo,
- AI pomočnika,
- akcijske gumbe za shranjevanje, priljubljene in dokončanje.

Posebej preverimo, da mobilne spremembe ne pokvarijo namiznega ali tabličnega prikaza.

---

## 12. Preverjanje pred commitom

Pred commitom preverimo:

```bash
git status
```

Za frontend:

```bash
cd frontend
npm run build
```

Za backend:

```bash
cd backend
pytest
```

Če backend testi še niso pripravljeni, preverimo vsaj zagon aplikacije:

```bash
uvicorn app.main:app --reload
```

Pred commitom preverimo tudi:

- ni dodanih `.env` datotek,
- ni dodanih API ključev ali gesel,
- ni nepotrebnih sprememb v nepovezanih datotekah,
- dokumentacija ima pravilne povezave,
- sprememba je skladna s pravili poimenovanja in pisanja kode.

---

## 13. Povzetek

Testiranje v projektu NIDiKo vključuje tehnično preverjanje frontenda in backenda ter ročno preverjanje glavnih uporabniških tokov.

Najpomembnejše je, da aplikacija po spremembah še vedno omogoča iskanje vsebin, pregled učnih poti, reševanje vprašalnika, prikaz rezultata, uporabo AI in glasovne pomoči ter spremljanje uporabniškega napredka.

## Sistemsko testiranje

- [Načrt vzdržljivostnega testa](17-nacrt-sistemskega-testiranja.md)
- [Poročilo sistemskega testiranja](18-porocilo-sistemskega-testiranja.md)
- [Orodja in navodila](../tests/performance/README.md)

Pilot na stagingu je izveden; vzdržljivostni zagon poteka z dokumentirano prekinitvijo generatorja in brez ponovitve. Izvedbe ne obravnavamo kot osmih neprekinjenih ur obremenitve. Dejanske meritve in omejitve so v poročilu sistemskega testiranja.
