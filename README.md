# ADM Agent Setup

Konfigurácia kódovacieho agenta (Claude Code) pre prácu na WooCommerce e-shopoch
slovenských klientov. Vlastný MCP server, päť doménových skillov, štyria subagenti
s obmedzenými právami a dva hooky, ktoré vynucujú pravidlá, na ktoré inštrukcia
nestačí.

**Bez pluginov a bez marketplace.** Všetko v repe je písané pre tento setup.

---

## Čo je vnútri

| Vrstva | Počet | Kde |
|---|---|---|
| MCP servery | 3 (1 vlastný) | `.mcp.json`, `mcp-servers/woo-mcp/` |
| Skills | 5 | `.claude/skills/` |
| Subagenti | 4 | `.claude/agents/` |
| Slash príkazy | 3 | `.claude/commands/` |
| Hooky | 2 (oba otestované) | `.claude/hooks/` |
| CI | 1 workflow | `.github/workflows/` |

Ako to do seba zapadá vrátane diagramu: [docs/architektura.md](docs/architektura.md)
Prečo je to postavené takto: [docs/rozhodnutia.md](docs/rozhodnutia.md)

---

## Inštalácia

Treba [uv](https://docs.astral.sh/uv/) a Node.js. Nič iné.

```bash
git clone <adresa-repa> adm-agent-setup
cd adm-agent-setup

cd mcp-servers/woo-mcp && uv sync && cd ../..

cp .env.example .env      # nepovinné, bez neho beží všetko na demo dátach
python overit.py          # kontrola, že je setup kompletný
claude
```

Overenie musí skončiť riadkom:

```
bez nalezov - setup je v poriadku
```

Bez `.env` beží MCP server v režime `fixtures` — číta demo dáta zo súborov, takže
celý setup sa dá vyskúšať bez prístupu k akémukoľvek e-shopu.

---

## MCP servery

| Server | Pôvod | Na čo |
|---|---|---|
| **`woo`** | **vlastný** | 8 nástrojov nad WooCommerce REST API |
| `playwright` | tretia strana | vizuálna kontrola e-shopu v prehliadači |
| `fetch` | tretia strana | načítanie stránky alebo dokumentácie |

### `woo` — vlastný server

Osem nástrojov: `server_status`, `search_products`, `get_product`, `check_stock`,
`list_orders`, `audit_seo`, `update_product`, `set_alt_text`.
Dokumentácia: [mcp-servers/woo-mcp/README.md](mcp-servers/woo-mcp/README.md)

Päť vecí, ktoré ho odlišujú od generického HTTP MCP servera:

1. **Šetrí kontext.** WooCommerce vracia na produkt vyše 60 polí. `search_products`
   ich oreže na osem, zvyšok si agent vypýta cez `get_product` len pre produkt, ktorý
   ho naozaj zaujíma.
2. **Zápis má štyri režimy.** `fixtures` (offline), `store` (verejné Store API,
   reálne dáta, iba čítanie **bez kľúčov**), `dry-run` (wc/v3 naživo, zapisuje
   naprázdno), `live`. Default je `fixtures`, takže server sa nedá spustiť omylom
   v zápisovom režime. Mimo `live` vráti `update_product` tabuľku predtým/potom.
3. **Vie doménu.** `audit_seo` hľadá chýbajúce alt texty, krátke popisy, názvy nad
   70 znakov a rizikovú diakritiku — veľké Š, Č, Ť, Ž v názve, ktoré subset fontu
   bez slovenských mäkčeňov zobrazí ako prázdne miesto.
4. **Nezamlčí, čo nevidel.** Stránkuje nad hranicou 100 položiek, ktorú WooCommerce
   vnucuje, kontroluje aj fotky jednotlivých variantov a orezaný výsledok vždy označí
   poľom `upozornenie`. Ticho neúplný audit je horší než žiadny.
5. **Nezmaže fotky pri oprave alt textu.** Pole `images` vo WooCommerce nahradí celú
   galériu, nie len poslaný obrázok — naivná oprava alt textu produkt oholí o zvyšné
   fotky a REST to potvrdí ako úspech. `set_alt_text` galériu načíta, doplní a pošle celú.

Nástroje sú označené `ToolAnnotations`, takže klient vie, ktoré sú bezpečné volať
bez pýtania a ktoré menia dáta.

---

## Skills

Každý skill je adresár s krátkym `SKILL.md` a detailmi v `references/` a `scripts/`,
ktoré sa načítajú až keď treba.

| Skill | Rieši |
|---|---|
| `woo-novy-produkt` | produkt end-to-end: SKU, varianty, alt texty, sklad, hromadné dávky z CSV |
| `sk-eshop-pravne` | povinné texty podľa zákona 108/2024, formulár na odstúpenie, cookies |
| `elementor-api` | vkladanie widgetov cez `$e.run` — drag & drop cez automatizáciu nefunguje |
| `wp-rest-prehliadac` | úpravy WordPressu cez REST z konzoly, nonce, nahrávanie fotiek |
| `klient-report` | odovzdávací dokument vo formáte ADM Technics |

Dva zo skillov nesú spustiteľné skripty:
`priprav_davku.py` skontroluje CSV dávku produktov pred zápisom,
`upload_media.js` nahrá fotky do knižnice médií cez canvas (base64 WordPress odmieta).

---

## Subagenti

| Agent | Model | Nástroje | Prečo samostatne |
|---|---|---|---|
| `eshop-auditor` | opus | 9, **iba čítanie** | audit zaberie tisíce tokenov, hlavné vlákno ich nepotrebuje |
| `woo-data-editor` | sonnet | 8, zápis cez woo | jediný, ktorý smie meniť dáta |
| `sk-copywriter` | sonnet | 3, bez kódu | písanie textov nepotrebuje prístup k súborom e-shopu |
| `php-reviewer` | haiku | 3, iba čítanie | mechanická kontrola vzorov, netreba na ňu drahý model |

Obmedzenie práv nie je inštrukcia, ktorú model môže obísť — audítor a reviewer
zápisové nástroje jednoducho nemajú.

---

## Slash príkazy

| Príkaz | Čo spraví |
|---|---|
| `/audit-eshop [oblasť]` | spustí `eshop-auditor` a vráti nálezy podľa závažnosti |
| `/novy-produkt [SKU]` | prevedie pridaním produktu vrátane textov a kontroly duplicity |
| `/report [klient] [typ]` | spíše odovzdávací dokument podľa šablóny |

---

## Hooky

| Hook | Udalosť | Čo robí |
|---|---|---|
| `guard_wp_core.py` | `PreToolUse` na Write/Edit | zamietne zápis do `wp-includes`, `wp-admin`, cudzieho pluginu a rodičovskej témy; povolí child tému a vlastné ADM pluginy |
| `session_context.py` | `SessionStart` | vpichne do kontextu režim MCP servera, stav `.env` a git vetvu |

Oba hooky majú vlastnú testovaciu sadu:

```bash
python .claude/hooks/test_guard.py             # 10 prípadov
python .claude/hooks/test_session_context.py   # 12 prípadov
```

Bez testu guardu by hook buď blokoval legitímnu prácu v child téme, alebo prepúšťal
zápisy do jadra. Oboje je horšie než žiadny hook.

Test `session_context.py` porovnáva jeho zoznam režimov s `PLATNE_REZIMY` v MCP
klientovi. Presne toto raz prekĺzlo: režim `store` pribudol do servera, ale nie do
hlásenia hooku, takže každá relácia začínala hláškou „neznámy režim".

---

## Overenie

Všetko sa dá reprodukovať bez e-shopu a bez sieťového prístupu k WooCommerce:

```bash
python overit.py                                    # celý setup
python .claude/hooks/test_guard.py                  # hook, 10 prípadov
python .claude/hooks/test_session_context.py        # hook, 12 prípadov
cd mcp-servers/woo-mcp
uv run python -m pytest tests/ -q                   # MCP server, 44 testov
uv run python smoke_stdio.py                        # skutočný MCP handshake cez stdio
```

Zachytené výstupy všetkých piatich: [docs/demo/overenie.md](docs/demo/overenie.md)

To isté beží pri každom pushi cez GitHub Actions:
[.github/workflows/kontrola.yml](.github/workflows/kontrola.yml). Rozpor medzi
konfiguráciou a kódom tak spadne hneď, nie až pri odovzdávke.

### Že to naozaj beží bez pluginov

`overit.py` zamietne konfiguráciu, ktorá obsahuje `enabledPlugins` alebo
`extraKnownMarketplaces`. V repe nie je jediný odkaz na marketplace.

Na spustenie s výhradne týmito MCP servermi, bez ohľadu na používateľskú konfiguráciu:

```bash
claude --strict-mcp-config --mcp-config .mcp.json
```

Na spustenie v úplne čistom profile sa dá presmerovať konfiguračný adresár cez
premennú `CLAUDE_CONFIG_DIR`.

---

## Bezpečnosť

- API kľúče sú v `.env`, ktorý je v `.gitignore`. V repe je len `.env.example`.
- `overit.py` prehľadáva repo na vzory kľúčov (`ck_…`, `cs_…`, súkromné kľúče,
  heslá v kóde) a zlyhá, ak niečo nájde.
- `.claude/settings.json` zakazuje čítanie `.env`, `git push --force` a `rm -rf`.
- Zápisové MCP nástroje sú v `permissions.ask`, čítacie v `allow` — potvrdenie sa
  pýta len tam, kde má význam. `overit.py` navyše kontroluje, že každý nástroj,
  na ktorý sa konfigurácia odvoláva, v serveri naozaj existuje — oprávnenie pre
  neexistujúci nástroj nechráni nič.
- V dokumentácii a demo dátach je `example-shop.sk`, žiadna reálna klientska doména.

---

## Štruktúra

```
adm-agent-setup/
├── CLAUDE.md                    pravidlá projektu
├── .mcp.json                    MCP servery
├── .env.example                 vzor prístupov
├── overit.py                    kontrola celého setupu
├── .github/workflows/           CI: všetky overenia pri každom pushi
├── .claude/
│   ├── settings.json            oprávnenia a hooky
│   ├── agents/                  4 subagenti
│   ├── skills/                  5 skillov
│   ├── commands/                3 slash príkazy
│   └── hooks/                   2 hooky + testy k obom
├── mcp-servers/woo-mcp/         vlastný MCP server
│   ├── src/woo_mcp/             server.py, client.py
│   ├── fixtures/                demo dáta
│   ├── tests/                   44 testov
│   └── smoke_stdio.py           overenie cez skutočný MCP protokol
└── docs/
    ├── architektura.md          diagram a dôvody
    ├── rozhodnutia.md           denník rozhodnutí
    └── demo/overenie.md         zachytené výstupy
```

---

Martin Mutka · ADM Technics · august 2026
