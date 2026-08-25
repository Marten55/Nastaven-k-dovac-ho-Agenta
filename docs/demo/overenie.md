# Overenie setupu — zachytené výstupy

Všetky výstupy nižšie sú skutočné, nie ilustračné. Nad každým blokom je príkaz,
ktorým sa dajú zopakovať. Nič z toho nepotrebuje živý e-shop ani API kľúče.

Prostredie overenia: Windows 11 · Python 3.12.13 · uv 0.11.33 · Node 25.9.0 · MCP SDK 2.1.0 · 25. 8. 2026

## 1. Validácia celého repa

Kontroluje JSON, BOM, frontmatter skillov a subagentov, rozbité odkazy na
referencie, prítomnosť prihlasovacích údajov a to, že nie je zapnutý žiadny plugin.

```
$ python overit.py
suborov: 44 | skillov: 5 | subagentov: 4 | prikazov: 3
bez nalezov - setup je v poriadku
```

## 2. Testy MCP servera

```
$ cd mcp-servers/woo-mcp && uv run python -m pytest tests/ -q
============================= 16 passed in 0.72s ==============================
```

Testy pokrývajú aj to, že výpis produktu je orezaný na osem polí, že `update_product`
mimo režimu `live` nič nezapíše a že server sa odmietne spustiť s neplatným režimom
alebo bez prihlasovacích údajov.

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
  [W] update_product   Uprav produkt. V rezime fixtures a dry-run vrati IBA nahlad zmeny.

server_status -> rezim=fixtures, zapis=False
audit_seo     -> skontrolovanych 6, s problemom 4
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
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "## Stav projektu (SessionStart hook)\n\n- woo MCP rezim: **fixtures** - OFFLINE demo data z mcp-servers/woo-mcp/fixtures/ - cisla NIE su stav realneho e-shopu, neprezentuj ich klientovi\n- .env: CHYBA - skopiruj .env.example na .env\n- git vetva: -\n- k dispozicii: 5 skillov, 4 subagentov, 3 prikazov"}}
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
