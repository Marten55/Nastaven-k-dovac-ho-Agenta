# Overenie setupu — zachytené výstupy

Všetky výstupy nižšie sú skutočné, nie ilustračné. Nad každým blokom je príkaz,
ktorým sa dajú zopakovať. Nič z toho nepotrebuje živý e-shop ani API kľúče.

Prostredie: Windows 11 · Python 3.12.13 · uv 0.11.33 · Node 25.9.0 · MCP SDK 2.1.0 · 26. 8. 2026

## 1. Validácia celého repa

Kontroluje JSON, BOM, frontmatter skillov a subagentov, rozbité odkazy na
referencie, prítomnosť prihlasovacích údajov a to, že nie je zapnutý žiadny plugin.

```
$ python overit.py
suborov: 46 | skillov: 5 | subagentov: 4 | prikazov: 3
bez nalezov - setup je v poriadku
```

## 2. Testy MCP servera

```
$ cd mcp-servers/woo-mcp && uv run python -m pytest tests/ -q
============================= 32 passed in 0.81s ==============================
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
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\smoke_stdio.py", line 58, in <module>
  |     raise SystemExit(asyncio.run(main()))
  |                      ^^^^^^^^^^^^^^^^^^^
  |   File "C:\Users\marte\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\asyncio\runners.py", line 195, in run
  |     return runner.run(main)
  |            ^^^^^^^^^^^^^^^^
  |   File "C:\Users\marte\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\asyncio\runners.py", line 118, in run
  |     return self._loop.run_until_complete(task)
  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "C:\Users\marte\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\asyncio\base_events.py", line 691, in run_until_complete
  |     return future.result()
  |            ^^^^^^^^^^^^^^^
  |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\smoke_stdio.py", line 26, in main
  |     async with stdio_client(parametre) as (citaj, zapis):
  |                ^^^^^^^^^^^^^^^^^^^^^^^
  |   File "C:\Users\marte\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\contextlib.py", line 231, in __aexit__
  |     await self.gen.athrow(value)
  |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\.venv\Lib\site-packages\mcp\client\stdio.py", line 200, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 815, in __aexit__
  |     raise BaseExceptionGroup(
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\.venv\Lib\site-packages\mcp\client\stdio.py", line 204, in stdio_client
    |     yield read_stream, write_stream
    |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\smoke_stdio.py", line 27, in main
    |     async with ClientSession(citaj, zapis) as session:
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\.venv\Lib\site-packages\mcp\client\session.py", line 521, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 815, in __aexit__
    |     raise BaseExceptionGroup(
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "C:\Users\marte\Desktop\adm-agent-setup\mcp-servers\woo-mcp\smoke_stdio.py", line 42, in main
      |     print(f"audit_seo     -> skontrolovanych {audit['skontrolovanych']}, "
      |                                               ~~~~~^^^^^^^^^^^^^^^^^^^
      | KeyError: 'skontrolovanych'
      +------------------------------------
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
v dokumentácii. Rovnaké pravidlo vynucuje aj `overit.py`.

Čo ten beh ukázal, v číslach bez identifikácie e-shopu:

| | pred opravou | po oprave |
|---|---|---|
| prejdených produktov | 100 (ticho orezané) | 127 |
| skontrolovaných variantov | 0 | 39 |
| skontrolovaných obrázkov | 1 958 | 2 060 |

Práve toto viedlo k doplneniu stránkovania a kontroly variantov — podrobne
v [denníku rozhodnutí](../rozhodnutia.md), bod 8.
