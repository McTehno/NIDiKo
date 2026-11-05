# Funkcionalno testiranje s Selenium WebDriver

Python Selenium je primeren za React uporabniski vmesnik: preizkusi tecejo v
pravem Chromu brez graficnega vmesnika (`--headless=new`). Selenium Manager
priskrbi ustrezen gonilnik; runner potrebuje Chrome in omrezje za njegov prenos.
Namestitev: `python -m pip install -r backend/requirements.txt`.

## Polni preizkus staging okolja

Iz korena repozitorija:

```sh
python backend/tests/functional/run_functional_tests.py --base-url http://46.225.17.135 --output-dir test-results/functional
```

Mapa mora biti nova. Skripta preveri vseh sest scenarijev (23 korakov), shrani
PNG in JSON ter vrne izhod 1 ob neuspehu ali manjkajocem koraku. GitHub Actions
jo zazene po namestitvi, pocaka na UI in API ter tudi ob napaki objavi dokaze
kot artifact in tabelo rezultatov. Zahteva zagnan frontend, backend, MongoDB
z vsebinami `up_001`, `mod_014`, `ue_036` in delujoc Supabase Auth.
Ne potrebuje prijavljenega testnega racuna; prijava je negativni primer.
Obstoj teh vsebin ni nadomestilo za loceno, ponovljivo testno bazo.

## Prijavni UI z nadzorovanim odgovorom

Za preverjanje prevoda `invalid_credentials` neodvisno od izpada Supabase:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5179 --strictPort
# V drugem terminalu iz korena repozitorija:
python backend/tests/functional/run_auth_ui_test.py --output-dir test-results/auth-ui
```

Frontend potrebuje veljavno oblikovan `VITE_SUPABASE_URL` in neprazen
`VITE_SUPABASE_ANON_KEY`. Za ta kontrolirani preizkus zadostujeta
`https://functional-test.supabase.co` in `functional-test-anon-key`.
Skripta v pravem brskalniku izpolni prijavni obrazec, za tocno en Auth endpoint
vrne HTTP 400 `invalid_credentials` in preveri sporocilo, URL ter odsotnost
shranjene seje. Nadomestek deluje samo za lokalni frontend. To je funkcionalni
test uporabniskega vmesnika z nadomesceno zunanjo storitvijo; ne potrjuje
dejanskega Supabase ali celotnega E2E. Rezultat: `summary.json`, `login.png`,
izhod 0/1. Polni staging test se vedno uporablja pravo storitev.

## Namerno vnesena napaka

1. Najprej izvedi zgornji test: pricakovan PASS / izhod 0.
2. V `frontend/src/pages/LoginPage/LoginPage.tsx` pri prevodu
   `Invalid login credentials` zamenjaj besedilo
   `Napačen e-poštni naslov ali geslo.` z `NAPAKA MUTACIJE`.
3. Ponovi isto skripto v novo izhodno mapo: pricakovan FAIL / izhod 1.
4. Povrni prevod in ponovi: pricakovan PASS / izhod 0.

Spreminja se implementacija aplikacije, ne pricakovanje testa. Napaka ne sme
ostati v koncni kodi. Dokazi in dejanski rezultati so v
`docs/20-avtomatizirano-funkcionalno-testiranje.md`.
