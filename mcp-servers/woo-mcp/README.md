# woo-mcp

MCP server nad WooCommerce REST API. Vlastná implementácia, nie obal cez tretiu stranu.

## Prečo vlastný server

Univerzálny HTTP MCP server by e-shop obslúžil tiež, ale za cenu kontextu a bezpečnosti:

- WooCommerce vracia na jeden produkt vyše 60 polí. `search_products` ich oreže na 8,
  takže výpis 20 produktov stojí stovky tokenov namiesto tisícov.
- Zápis je za trojstupňovým režimom, takže sa nedá „omylom naživo".
- `audit_seo` je doménová kontrola, ktorú generický server nevie — vrátane rizikovej
  diakritiky v názvoch (subset fontu bez slovenských mäkčeňov ich zobrazí ako medzeru).

## Režimy

Riadi ich premenná `WOO_MODE`, default je `fixtures`, teda najbezpečnejšia možnosť.

| Režim | Čítanie | Zápis | Použitie |
|---|---|---|---|
| `fixtures` | z `fixtures/*.json` | vráti náhľad | demo, testy, vývoj bez e-shopu |
| `dry-run` | naživo cez REST | vráti náhľad | príprava hromadnej zmeny na ostrých dátach |
| `live` | naživo cez REST | zapíše | ostrá prevádzka |

Server sa v režime `dry-run` a `live` odmietne spustiť bez kompletných prihlasovacích
údajov a povie, čo chýba.

## Nástroje

| Nástroj | Čo robí |
|---|---|
| `server_status` | v akom režime beží a na aký e-shop je napojený |
| `search_products` | hľadanie podľa názvu/SKU, skrátený výpis |
| `get_product` | detail produktu podľa ID alebo SKU vrátane alt textov |
| `check_stock` | stav skladu podľa SKU vrátane `backorders` |
| `list_orders` | objednávky podľa stavu |
| `audit_seo` | chýbajúce alt texty, krátke popisy, dlhé názvy, riziková diakritika |
| `update_product` | úprava produktu, mimo `live` iba náhľad zmeny |

## Spustenie

```bash
uv sync
uv run woo-mcp          # stdio, čaká na MCP klienta
```

Z koreňa repa ho spúšťa `.mcp.json`:

```json
"woo": {
  "command": "uv",
  "args": ["--directory", "./mcp-servers/woo-mcp", "run", "woo-mcp"]
}
```

## Testy

```bash
uv run python -m pytest tests/ -v
```

Testy bežia v režime `fixtures`, takže nepotrebujú e-shop ani sieť.

## Prihlasovacie údaje

WooCommerce → Nastavenia → Pokročilé → REST API → Pridať kľúč. Na audit stačí
oprávnenie *Čítanie*; *Čítanie/Zápis* nasadzuj až keď naozaj zapisuješ. Kľúče idú
do `.env` v koreni repa, ktorý je v `.gitignore`.

Pozor: WooCommerce posiela kľúče cez HTTP Basic, ktorý funguje len cez HTTPS.
Na `http://` sa autentifikácia tichšie rozbije a vráti 401.
