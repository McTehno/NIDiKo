# Načrt vzdržljivostnega testiranja

Status: pripravljena izvedba, **meritve na stagingu še niso bile opravljene**.

## Namen in obseg

Preveriti stabilnost obstoječe postavitve NIDiKo na CX23 pri večurnem reševanju
vprašalnikov. Gre za vzdržljivostni test, ne iskanje meje zmogljivosti.
Kolegov stresni test bo ločen preizkus v drugem terminu, s skupnim poročilom.
Rezultat velja za zabeleženo različico in okolje, ne za še neizvedene mikropotrdilne funkcije.

## Scenarij in pogoji

Orodje: Locust 2.47.0, en proces na ločenem generatorju. Zahteve prek javne
vstopne poti staginga, poti `/api/questionnaires`, `/api/assessments/evaluate`,
`/api/assessment-assistant/message`, `/api/voice-help/question` in prenos posnetka.
Sintetični aplikacijski profili v namenski staging bazi; prijava Supabase ni vključena.

- 100 stalno aktivnih mest; novo reševanje dobi nov profil.
- 40 mest uporablja AI; 5 od teh tudi enkrat na reševanje glasovno pomoč.
- Uteženo 1–20 sporočil AI na reševanje uporabnika AI; povprečje 4,06.
- Premori 15–35 s na vprašanje, dodatnih 10–25 s za branje pomoči.
- Postopno dodajanje 1 uporabnika/s, 5 minut ogrevanja, 8 ur ciljnega režima,
  2 minuti opazovanja po odstranitvi obremenitve.
- Prva različica uporablja izbrano učno pot in vprašanja DA/NE. Izbor, število
  vprašanj in začetno stanje glasovnega predpomnilnika se zabeležijo pred izvedbo.

Deleži in časi so predpostavke testnega modela, ne podatki dejanske uporabe.
Kratek pilot mora potrditi število potrebnih profilov, realistično trajanje poti,
oceno stroška in kvote AI, govora, baze in prenosa posnetkov. Testna baza mora
biti tista, ki jo uporablja testirani staging, in mora vsebovati izbrano učno pot.

## Kriteriji

| Skupina | Kriterij |
|---|---|
| Vsaka skupina zahtev | vsaj 99,9 % veljavnih uspešnih odgovorov |
| Pridobitev in oddaja vprašalnika, vsaka posebej | vsaj 99 % vseh zahtev uspešnih v največ 400 ms |
| Besedilni AI | vse zahteve uspešne v največ 7 s do celotnega odgovora |
| Pripravljena glasovna pomoč | API največ 3 s; celoten prenos posnetka ločeno največ 3 s |
| Prvo ustvarjanje glasu | ločen prikaz časov, časovni prag še ni določen |

Trenutna izvedba ne meri časa od klika do začetka predvajanja. Dve ločeni
trisekundni meji nista skupna trisekundna meja. Pred glavnim zagonom potrditi,
ali to zadostuje ali je potrebna dodatna meritev v brskalniku.

Pragovi se ocenijo skupno in prikažejo v petminutnih intervalih. Infrastruktura:
poraba RAM, load, prosti disk in razpoložljive meritve procesov/vsebnikov,
ponovni zagoni, zunanje kvote. Za stabilnost virov še ni numeričnih pragov:
samodejni PASS HTTP dela zato ni končni sklep o infrastrukturi. Pred testom
se popiše dejanska konfiguracija in dostopni viri meritev.

## Nespremenljivost okolja in sledljivost

Pred začetkom zabeležiti aplikacijski commit, testni commit, konfiguracijo
procesov, bazo, zunanje storitve, strežniške vire, UTC čas in identifikator zagona.
Na GitHubu nastaviti repository variable `STAGING_DEPLOY_PAUSED=true` ter počakati,
da se vse tekoče namestitve zaključijo. Varovalo prepreči nove deploy jobe;
ne ustavi že tekoče namestitve in ne blokira ročnih posegov na strežniku.
Dejanski `/var/www/psi-up/deploy-staging.sh` ni del pregledanega repozitorija;
njegovo vsebino, način zagona in dejanski nameščeni commit je treba preveriti.
Po testu odstraniti premor in izrecno namestiti izbrano različico, saj preskočeni
deploy jobi ne čakajo v vrsti za samodejno poznejšo namestitev.

## Dokazi in omejitve

Surove meritve se zbirajo sproti na generatorju in stagingu, nato združijo po
identifikatorju zagona. `summary.json`, CSV, HTML in grafi služijo poročilu.
Manjkajoče skupine, prekinjen test ali nedosežena obremenitev niso uspeh.
Majhni vzorci so označeni; osem ur ni dokaz dolgoročne razpoložljivosti.
Predloge izboljšav je treba ločiti od dejansko dokazanih vzrokov.

Ponovljiva navodila: [testni sklop](../tests/performance/README.md).

## Pred glavnim zagonom še potrditi

1. Staging naslov, dejanski commit, deploy skripto in način zagona.
2. Namensko bazo, izbrano učno pot in velikost sklopa profilov po pilotu.
3. Dovoljeno domeno posnetkov, stanje predpomnilnika, strošek in kvote.
4. Dostopne infrastrukturne meritve in trajno delujoč generator.
5. Definicijo trisekundne glasovne meje ter termin brez drugih testov in namestitev.
