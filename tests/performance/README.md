# Vzdržljivostno testiranje NIDiKo

Test poteka proti javnemu naslovu **staginga**, z ločenega generatorja obremenitve.
Ne izvaja se ob običajnem pushu. Podpira en proces Locusta; porazdeljeni način in
`--processes` nista podprta (lokalno dodeljevanje profilov in zapisovanje dogodkov).

## Model

100 aktivnih mest: natanko 40 uporablja besedilno pomoč, 5 tudi glasovno pomoč.
Glasovni uporabniki so podmnožica uporabnikov AI. Po oddaji mesto začne novo
reševanje z novim profilom. Skupno število različnih oseb zato presega 100.
Za vsako reševanje se izbere 1–20 AI sporočil z utežmi iz profila. Povprečje je
4,06 sporočila na reševanje uporabnika AI. Sporočila so razporejena po vprašanjih,
možnih je več razjasnitev istega vprašanja. Pet odstotkov uporabnikov uporabi
glasovno pomoč enkrat na reševanje. To je dodatna eksplicitna predpostavka.

Premor za branje vprašanja: 15–35 s; po pomoči dodatnih 10–25 s. Med premori ni
umetnih API klicev. Vsi odgovori DA/NE se oddajo skupaj kot v aplikaciji.
Prvi profil vsebuje samo eno učno pot; izbiro in njeno število vprašanj je treba
pred dolgim testom potrditi. Drugi tipi vprašanj niso podprti in povzročijo napako.

## Priprava generatorja (PowerShell, iz korena repozitorija)

```powershell
python -m venv tests/performance/.venv
tests/performance/.venv/Scripts/python.exe -m pip install -r tests/performance/requirements.txt
tests/performance/.venv/Scripts/python.exe -m unittest discover -s tests/performance/checks -v
$env:PERF_BASE_URL = 'https://VAS-STAGING'
$env:PERF_MONGODB_URI = 'VREDNOST-IZ-UPRAVLJALNIKA-SKRIVNOSTI'
$env:PERF_DATABASE_NAME = 'nidiko_staging_test'
```

Za Linux uporabi `.venv/bin/python` in ustrezen način nastavitve okolja. Za 8 ur
uporabi trajno delujoč generator, npr. Linux s `tmux`; izklop in spanje nista dovoljena.
Datoteka `.env.example` je samo primer, ne samodejni nalagalnik okolja.

**Staging mora dejansko uporabljati isto namensko bazo**, ki jo navedeš pri pripravi.
Za pripravo potrebuješ omrežni dostop in pravice v tej bazi. Ne uporabljaj produkcijske baze.
Skripta ustvari sintetične aplikacijske profile, ne računov Supabase. Trenutna
API-ja vprašalnika in oddaje sprejmeta `user_id` brez prijave. Test zato ne meri
prijave, registracije, podaljševanja žetonov ali zaščitenih uporabniških poti.

```powershell
tests/performance/.venv/Scripts/python.exe tests/performance/scripts/prepare_test_data.py --count 5000 --target-id DEJANSKI-ID-UCNE-POTI --audio-host VAS-RACUN.blob.core.windows.net --output test-results/performance/pool.json --confirm-database nidiko_staging_test
```

Evidenco shrani pred vstavljanjem za možnost čiščenja tudi ob delni napaki. Poola
ne uporabljaj ponovno: že rešeni profili povzročijo predizpolnjevanje vprašanj.
Velikost 5000 je predlog, ne ocena zmogljivosti. Potrebno število določi iz kratkega
pilota (trajanje reševanja in hitrost menjave), z rezervo. Izčrpanje prekine zagon.
Skupni glasovni predpomnilnik in posnetki se ne brišejo. Njihovo začetno stanje
zabeleži; glavni test meri predvsem že pripravljeno pomoč, prvo ustvarjanje ločeno.

## Zagon

Pred izvedbo preveri dejanski staging commit, odsotnost tekoče namestitve,
sinhronizacijo ur, porabo in kvote zunanjih storitev. Med testom velja premor namestitev.

```powershell
tests/performance/.venv/Scripts/python.exe tests/performance/scripts/run_endurance.py --data test-results/performance/pool.json --app-commit DEJANSKI-COMMIT --environment-note 'CX22; dopolni procese, bazo, kvote in stanje predpomnilnika'
```

Ukaz brez `--execute` samo lokalno preveri konfiguracijo in izpiše oceno, brez zahtev.
Z `--execute` začne dejanski test. Prvi pilot izvedeš s kopijo JSON profila in krajšimi
časi ter 20 uporabniki; parametra `--profile` in `--output` omogočata ločene zagone.
Pilot ni dokaz osemurne vzdržljivosti. Privzeti profil vključuje približno 100 s
povečevanja, 300 s ogrevanja, **28800 s ciljne obremenitve** in 120 s opazovanja po
odstranitvi obremenitve. Okrevanje pomeni konec zahtev, ne 100 aktivnih uporabnikov.

Na stagingu pred začetkom zaženi zbiranje meritev in ga ustavi po okrevanju:

```bash
bash tests/performance/scripts/collect_metrics.sh /var/tmp/nidiko-perf/OZNAKA-ZAGONA 10
```

Meritve so osnovni indikatorji gostitelja (load, RAM, disk) in, če je na voljo Docker,
statistika vseh vsebnikov. Odsotnost Dockerja ne pomeni odsotnosti obremenitve!
Pri drugačnem zagonu je treba pred glavnim testom dodati spremljanje dejanskih
procesov ter ponovnih zagonov. Metrike baze in Azure kvot pridobi iz njihovih
obstoječih nadzornih plošč za isti UTC interval. Generator spremljaj ločeno.

## Rezultati in ocenjevanje

`test-results/performance/<UTC-oznaka>/` vsebuje manifest, profil, dnevnik,
Locust CSV in HTML, `events.jsonl`, `summary.json` in samostojen `report.html`
z grafi p99 po petminutnih intervalih. Dogodki se sproti zapisujejo in praznijo
medpomnilnik; datoteke ob prekinitvi ostanejo dostopne. Ne beležimo teles odgovorov,
žetonov ali podpisanih zvočnih povezav. `pool.json` je zasebna operativna evidenca.

Prenesi infrastrukturne meritve v podmapo istega zagona in arhiviraj mapo zunaj
repozitorija. Skripta jih ne prenaša samodejno in iz njih ne sklepa vzroka napak.
V Git sodijo načrt, kratko poročilo in izbrani anonimizirani grafi, ne surovi podatki.

Vsaka skupina zahtev mora doseči vsaj 99,9 % uspešnosti; običajni skupini vsaj
99 % uspešnih odgovorov v največ 400 ms (imenovalec so vse zahteve skupine).
Vse zahteve AI morajo biti uspešne v največ 7000 ms. Pripravljena glasovna pomoč:
API največ 3000 ms; prenos celotnega zvoka dodatno ločeno največ 3000 ms.
To **ni** kriterij treh sekund od klika do zvoka: ta končna uporabniška meritev še
ni vključena. Čas prvega ustvarjanja nima dogovorjenega praga, napake pa štejejo.

`PASS` opisuje opažene vzorce in ne dokazuje dolgoročne zanesljivosti. Majhen vzorec
(manj kot 1000 zahtev skupine) je označen. `FAIL` pomeni presežene kriterije;
`INVALID` prekinitev, manjkajočo ciljno obremenitev ali napako izvajanja;
`INCOMPLETE` manjkajočo zahtevano skupino. Časovna okna imajo lastne ocene za
odkrivanje poslabšanja; skupni PASS jih ne nadomesti in zahteva tudi ročno presojo
infrastrukture. CSV percentili Locusta so informativni; analiza uporablja točne čase.

Ponovna analiza in čiščenje (slednje privzeto samo izpiše obseg):

```powershell
tests/performance/.venv/Scripts/python.exe tests/performance/scripts/analyze_results.py test-results/performance/OZNAKA-ZAGONA
tests/performance/.venv/Scripts/python.exe tests/performance/scripts/cleanup_test_data.py test-results/performance/pool.json --confirm-pool PERF-OZNAKA-IZ-EVIDENCE
```

Čiščenje izvedi z `--execute` šele po koncu testa in arhiviranju. Odstrani samo
evidentirane sintetične profile ter pripadajoče AI seje in sporočila. Azure posnetki
in skupni predpomnilnik ostanejo. Ne zaganjaj čiščenja med meritvijo.

Referenci orodja: [uporabniški poteki](https://docs.locust.io/en/stable/writing-a-locustfile.html),
[zagon brez vmesnika](https://docs.locust.io/en/stable/running-without-web-ui.html).
