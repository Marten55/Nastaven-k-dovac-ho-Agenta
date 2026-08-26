# Overenie setupu — zachytené výstupy

Všetky výstupy nižšie sú skutočné, nie ilustračné. Nad každým blokom je príkaz,
ktorým sa dajú zopakovať. Nič z toho nepotrebuje živý e-shop ani API kľúče.
To isté beží pri každom pushi cez [CI](../../.github/workflows/kontrola.yml).

Prostredie tohto záznamu: Linux · Python 3.11.15 · uv 0.8.17 · MCP SDK 2.1.0 ·
httpx 0.28.1 · 26. 8. 2026. Setup sa vyvíja na Windows 11 v PowerShelli; výstupy
sú prenesené preto, že ich naposledy generovalo CI, a nie ručný beh na stanici.

## 1. Validácia celého repa

Kontroluje JSON, BOM, frontmatter skillov a subagentov, rozbité odkazy na
referencie, prihlasovacie údaje, zapnuté pluginy, to, že každý nástroj spomenutý
v konfigurácii v serveri naozaj existuje, a to, že zachytené výstupy v tomto
súbore nepochádzajú zo zlyhaného behu.

```
$ python overit.py
suborov: 48 | skillov: 5 | subagentov: 4 | prikazov: 3
bez nalezov - setup je v poriadku
```

## 2. Testy MCP servera

```
$ cd mcp-servers/woo-mcp && uv run python -m pytest tests/ -q
............................................                             [100%]
44 passed in 0.96s
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
- že `set_alt_text` pošle celú galériu, nie len menený obrázok — inak by
  WooCommerce zvyšné fotky z produktu zmazal
- že `set_alt_text` neodošle PUT, keď sa alt text nelíši od súčasného
- že `set_alt_text` odmietne ID obrázka, ktorý k produktu nepatrí
- že oba zápisové nástroje zlyhajú zrozumiteľne pri neexistujúcom produkte

## 3. MCP server naživo cez stdio

Skutočný MCP handshake: server beží ako samostatný proces, klient sa naň pripojí
cez stdio, vypýta si zoznam nástrojov a zavolá tri z nich. Značka `[R]` znamená
`read_only_hint`, `[W]` zápisový nástroj.

```
$ cd mcp-servers/woo-mcp && uv run python smoke_stdio.py
handshake OK -> server 'woo' v0.1.0

nastroje (8):
  [R] server_status    Zisti, v akom rezime server bezi a na aky e-shop je napojeny.
  [R] search_products  Najdi produkty podla nazvu alebo SKU. Vracia skrateny vypis.
  [R] get_product      Nacitaj jeden produkt podla ID alebo SKU vratane popisov a obrazkov.
  [R] check_stock      Over stav skladu jedneho produktu podla SKU.
  [R] list_orders      Vypis objednavky. stav: any, processing, completed, on-hold, cancelled.
  [R] audit_seo        Najdi produkty s chybami, ktore skodia SEO a zobrazeniu.
  [W] update_product   Uprav produkt. Mimo rezimu live vrati IBA nahlad zmeny.
  [W] set_alt_text     Doplni alebo prepise alt texty obrazkov produktu. Mimo `live` iba nahlad.

server_status -> rezim=fixtures, zapis=False
audit_seo     -> produktov 6, obrazkov 8, z toho bez alt textu 3
                 s problemom 4 produktov
   - XB47-0012    2 problem(ov)
   - FLT-2200     2 problem(ov)
   - HELM-0104    1 problem(ov)
   - OLEJ         1 problem(ov)

update_product -> vykonane=False (spravne False, lebo rezim je fixtures)
set_alt_text   -> meni sa 1 obrazok, 1 zostava nedotknuty

VSETKO OK
```

Posledný riadok je celý zmysel `set_alt_text`: produkt 104 má dva obrázky, mení sa
alt text jedného a druhý zostáva aj s vlastným altom. Naivný zápis cez `images`
by ten druhý z produktu odstránil.

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
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "## Stav projektu (SessionStart hook)\n\n- woo MCP rezim: **fixtures** - OFFLINE demo data z mcp-servers/woo-mcp/fixtures/ - cisla NIE su stav realneho e-shopu, neprezentuj ich klientovi\n- .env: CHYBA - skopiruj .env.example na .env\n- git vetva: claude/woocommerce-agent-review-7k729g\n- k dispozicii: 5 skillov, 4 subagentov, 3 prikazov"}}
```

## 6. Testy hooku so stavom projektu

Posledné štyri prípady porovnávajú zoznam režimov v hooku s `PLATNE_REZIMY`
v MCP klientovi. Bez toho prekĺzlo, že režim `store` pribudol do servera, ale
nie do hlásenia — relácia potom začínala hláškou „neznámy režim".

```
$ python .claude/hooks/test_session_context.py
OK    fixtures hlasi demo data           -> obsahuje 'OFFLINE demo data'
OK    store hlasi realne data            -> obsahuje 'REALNE data'
OK    store priznava, co nevracia        -> obsahuje 'objednavky'
OK    dry-run hlasi simulaciu            -> obsahuje 'simuluju'
OK    live hlasi plny zapis              -> obsahuje 'PLNY ZAPIS'
OK    live prida varovanie               -> obsahuje 'POZOR'
OK    preklep sa oznaci                  -> obsahuje 'NEZNAMY rezim'
OK    preklep vypise povolene            -> obsahuje 'dry-run'
OK    klient pozna 'dry-run'             -> hook ho pozna
OK    klient pozna 'fixtures'            -> hook ho pozna
OK    klient pozna 'live'                -> hook ho pozna
OK    klient pozna 'store'               -> hook ho pozna

12/12 testov preslo
```

## 7. Skript zo skillu `woo-novy-produkt`

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

## 8. Overenie na reálnom e-shope

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
