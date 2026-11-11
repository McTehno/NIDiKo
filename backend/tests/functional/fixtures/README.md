# Podatki za TS-NIDIKO-04 in TS-NIDIKO-05

Javni učni podatki, prebrani 11. 11. 2026 iz staging API:

- `http://46.225.17.135/api/modules/mod_014`
- `http://46.225.17.135/api/learning-units/ue_036`
- `http://46.225.17.135/api/learning-units/ue_031`
- `http://46.225.17.135/api/learning-units/ue_032`
- `http://46.225.17.135/api/learning-units/ue_033`

V repozitoriju so osnovni podatki `backend/data/nova_verzija_data`, vendar tam ni
modula `mod_014` in njegovih enot iz prejšnje naloge. Ti datoteki dopolnita lokalno
testno bazo z navedenimi vsebinami; med CI se staging API ne kliče. Ne vsebujeta
računov, prijavnih podatkov ali uporabniškega napredka. Obstoječa baza se ne spreminja.
