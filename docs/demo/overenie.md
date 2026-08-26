# Overenie setupu — zachytené výstupy

Všetky výstupy nižšie sú skutočné, nie ilustračné. Nad každým blokom je príkaz,
ktorým sa dajú zopakovať. Nič z toho nepotrebuje živý e-shop ani API kľúče.

Prostredie: Windows 11 · Python 3.12.13 · uv 0.11.33 · Node 25.9.0 · MCP SDK 2.1.0 · 26. 8. 2026

## 1. Validácia celého repa

Kontroluje JSON, BOM, frontmatter skillov a subagentov, rozbité odkazy na
referencie, prihlasovacie údaje, zapnuté pluginy a to, že zachytené výstupy
v tomto súbore nepochádzajú zo zlyhaného behu.

```
$ python overit.py
suborov: 46 | skillov: 5 | subagentov: 4 | prikazov: 3
bez nalezov - setup je v poriadku
```

## 2. Testy MCP servera

```
$ cd mcp-servers/woo-mcp && uv run python -m pytest tests/ -q
============================= 32 passed in 0.86s ==============================
```

Dva súbory. `test_server.py` beží v režime `fixtures`, `test_store_mode.py` má
zamockované HTTP. Ani jeden nepotrebuje e-shop ani sieť. Pokrývajú okrem iného:

- stránkovanie nad hranicou 100 položiek, ktorú WooCommerce vnucuje
- poistku proti nekonečnému stránkovaniu a označenie orezaného výsledku
- normalizáciu tvaru zo Store API (ceny v centoch, popisy ako HTML)
- že sa režim `store` nikdy nezavolá s prihlasovacími údajmi
- že `wc/v3` filtruje na `status=publish`, aby nevracal produkty v koši
- načítanie fotiek jednotlivých variantov a ich započítanie do auditu
- že vypnutý rozsah sa prizná v poli `nekontrolovane`

## 3. MCP server naživo cez stdio

Skutočný MCP handshake: server beží ako samostatný proces, klient sa naň pripojí
cez stdio, vypýta si zoznam nástrojov a zavolá tri z nich. Značka `[R]` znamená
`read_only_hint`, `[W]` zápisový nástroj.

```
$ cd mcp-servers/woo-mcp && uv run python smoke_stdio.py
handshake OK -> server 'woo' v0.1.0

nastroje (7):
  [R] server_status    Zisti, v akom rezime server bezi a na aky e-shop je napojeny.
  [R] search_products  Najdi produkty podla nazvu alebo SKU. Vracia skrateny vypis.
  [R] get_product      Nacitaj jeden produkt podla ID alebo SKU vratane popisov a obrazkov.
  [R] check_stock      Over stav skladu jedneho produktu podla SKU.
  [R] list_orders      Vypis objednavky. stav: any, processing, completed, on-hold, cancelled.
  [R] audit_seo        Najdi produkty s chybami, ktore skodia SEO a zobrazeniu.
  [W] update_product   Uprav produkt. Mimo rezimu live vrati IBA nahlad zmeny.

server_status -> rezim=fixtures, zapis=False
audit_seo     -> produktov 6, obrazkov 8, z toho bez alt textu 3
                 s problemom 4 produktov
   - XB47-0012    2 problem(ov)
   - FLT-2200     2 problem(ov)
   - HELM-0104    1 problem(ov)
   - OLEJ         1 problem(ov)

update_product -> vykonane=False (spravne False, lebo rezim je fixtures)

VSETKO OK
```

## 4. Hook, ktorý blokuje zápis do cudzieho kódu

```
$ python .claude/hooks/test_guard.py
OK    Windows cesta do cudzieho pluginu    -> deny
OK    unix cesta do cudzieho pluginu       -> deny
OK    vlastny ADM plugin                   -> allow
OK    child tema                           -> allow
OK    rodicovska tema                      -> deny
OK    wp-includes                          -> deny
OK    wp-admin                             -> deny
OK    wp-config.php                        -> deny
OK    mu-plugin ADM                        -> allow
OK    bezny subor v repe                   -> allow

10/10 testov preslo
```

## 5. Hook, ktorý vpichuje stav projektu na začiatku relácie

```
$ echo {} | python .claude/hooks/session_context.py
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "## Stav projektu (SessionStart hook)\n\n- woo MCP rezim: **fixtures** - OFFLINE demo data z mcp-servers/woo-mcp/fixtures/ - cisla NIE su stav realneho e-shopu, neprezentuj ich klientovi\n- .env: CHYBA - skopiruj .env.example na .env\n- git vetva: main\n- k dispozicii: 5 skillov, 4 subagentov, 3 prikazov"}}
```

## 6. Skript zo skillu `woo-novy-produkt`

Kontrola CSV dávky pred zápisom do e-shopu. Vracia nenulový návratový kód,
takže sa dá zapojiť do dávkového spracovania.

```
$ python .claude/skills/woo-novy-produkt/scripts/priprav_davku.py \
      .claude/skills/woo-novy-produkt/scripts/priklad.csv
riadok 4 (OLEJ):
    - SKU 'OLEJ' neobsahuje cislo - over konvenciu
    - chyba kratky popis
    - cena '8,90' ma desatinnu ciarku - WooCommerce chce bodku
    - chyba alt text

3 riadkov, 2 v poriadku, 1 s chybou

Chybne riadky oprav v CSV a spusti znova. Nic sa nezapisalo.
```

## 7. Overenie na reálnom e-shope

Režim `store` bol otestovaný aj proti živému WooCommerce e-shopu s katalógom
127 produktov. Výstup z toho behu tu **zámerne nie je** — obsahuje doménu
klienta a `CLAUDE.md` tohto projektu zakazuje reálne klientske domény
v dokumentácii.

Čo ten beh ukázal, v číslach bez identifikácie e-shopu:

| | pred opravou | po oprave |
|---|---|---|
| prejdených produktov | 100 (ticho orezané) | 127 |
| skontrolovaných variantov | 0 | 39 |
| skontrolovaných obrázkov | 1 958 | 2 060 |

Práve toto viedlo k doplneniu stránkovania a kontroly variantov — podrobne
v [denníku rozhodnutí](../rozhodnutia.md), bod 8.
