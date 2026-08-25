# ADM Technics — pravidlá projektu

Setup kódovacieho agenta pre prácu na WooCommerce/WordPress e-shopoch pre slovenských
klientov. Tento súbor je nadradený default správaniu agenta.

## Jazyk a výstup

- Všetko klientovi smerujúce píš **po slovensky**, vrátane diakritiky.
- Formát odovzdávky: číslovaný brief hore, potom handover rozdelený podľa **kto** to
  spraví (klient / ADM / agent), s explicitným „čaká sa na …" namiesto plochého TODO.
- Ceny a licenčné poplatky uvádzaj vždy konkrétne, nie „podľa rozsahu".
- Prihlasovacie údaje nikdy nepíš do dokumentov, ktoré idú klientovi.

## Prostredie

- Windows 11, primárne PowerShell. Bash je k dispozícii, ale cesty píš s `/` alebo
  ich uveď v úvodzovkách — v cestách sú medzery aj diakritika (`D:\HTML stránky\…`).
- Balíčkovač na PATH nie je. Užívateľské binárky patria do `~/.local/bin`, Python cez `uv`.
- Nikdy nenavrhuj `apt`, `brew` ani inštalátor vyžadujúci admina.

## Práca s WordPressom

- **Nikdy needituj cudzí kód**: `wp-content/plugins/`, `wp-includes/`, `wp-admin/` ani
  súbory rodičovskej témy. Úpravy idú do child témy alebo do vlastného snippetu.
  Toto vynucuje aj hook `guard_wp_core.py` — keď ťa zastaví, nehľadaj obchádzku.
- Zmeny na produkcii rob cez REST API alebo snippet, nie cez editor súborov v admine.
- Pred hromadnou zmenou nad 20 produktmi si vyžiadaj potvrdenie a najprv ukáž náhľad
  (`WOO_MODE=dry-run`).

## MCP server `woo`

- Beží v troch režimoch: `fixtures` (offline, default), `dry-run` (číta naživo, zapisuje
  naprázdno), `live` (plný zápis). Režim čítaj z odpovede nástroja, nepredpokladaj ho.
- Ak je režim `fixtures`, čísla sú demo dáta — nikdy ich neprezentuj ako stav e-shopu.

## Bezpečnosť

- API kľúče žijú v `.env`, ktorý je v `.gitignore`. Do repa, do reportu ani do chatu
  ich nekopíruj.
- V dokumentácii a demo výstupoch používaj `example-shop.sk`, nie reálne klientske domény.

## Kedy siahnuť po subagentovi

- Audit e-shopu → `eshop-auditor` (read-only, nič nezapíše).
- Hromadné zápisy cez `woo` MCP → `woo-data-editor`.
- Slovenské texty produktov a kategórií → `sk-copywriter`.
- Kontrola PHP/JS snippetu pred nasadením → `php-reviewer`.

Hlavné vlákno nech si nesťahuje do kontextu celý výpis produktov — na to je subagent.
