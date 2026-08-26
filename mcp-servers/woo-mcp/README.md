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

| Režim | Čítanie | Zápis | Kľúče | Použitie |
|---|---|---|---|---|
| `fixtures` | z `fixtures/*.json` | náhľad | nie | demo, testy, vývoj bez e-shopu |
| `store` | verejné Store API | zamietne | **nie** | audit cudzieho e-shopu bez prístupov |
| `dry-run` | wc/v3 naživo | náhľad | áno | príprava hromadnej zmeny na ostrých dátach |
| `live` | wc/v3 naživo | zapíše | áno | ostrá prevádzka |

Server sa v režime `dry-run` a `live` odmietne spustiť bez kompletných prihlasovacích
údajov a povie, čo chýba. Režimu `store` stačí `WOO_BASE_URL`.

### Prečo režim `store`

Audit e-shopu treba spraviť najčastejšie **skôr, než klient vygeneruje API kľúče** —
pri obhliadke pred ponukou, pri prevzatí cudzieho webu, pri kontrole po zásahu.
Store API je to isté rozhranie, z ktorého číta výkladná skriňa e-shopu: vráti názov,
SKU, krátky popis, kategórie aj obrázky s alt textami. Zápis cezeň nejde, takže
sa v tomto režime nedá nič pokaziť ani omylom.

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

### Stránkovanie a varianty

WooCommerce vráti najviac **100 položiek** na požiadavku bez ohľadu na to, čo pošleš.
`search_products` aj `audit_seo` preto stránkujú automaticky. Keby to nerobili, pri
katalógu nad 100 produktov by audit ticho vynechal zvyšok a hlásil menej nálezov,
než ich naozaj je. Keď sa narazí na poistku proti nekonečnému stránkovaniu, výsledok
sa označí poľom `upozornenie` — orezaný výstup sa nikdy netvári ako úplný.

`audit_seo` má `zahrn_varianty=True`. Fotka varianty sa na e-shope zobrazí až po
prepnutí farby, takže audit, ktorý pozerá len na rodičovský produkt, ju nikdy neuvidí.
Na reálnom katalógu so 127 produktmi to znamenalo rozdiel medzi 1 958 a 2 060
kontrolovanými obrázkami.

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

32 testov v dvoch súboroch. `test_server.py` beží v režime `fixtures`,
`test_store_mode.py` má zamockované HTTP — ani jeden nepotrebuje e-shop ani sieť.
Pokrývajú okrem iného stránkovanie nad 100 položiek, normalizáciu tvaru zo Store API,
načítanie fotiek variantov a to, že `store` sa nikdy nezavolá s prihlasovacími údajmi.

## Prihlasovacie údaje

WooCommerce → Nastavenia → Pokročilé → REST API → Pridať kľúč. Na audit stačí
oprávnenie *Čítanie*; *Čítanie/Zápis* nasadzuj až keď naozaj zapisuješ. Kľúče idú
do `.env` v koreni repa, ktorý je v `.gitignore`.

Pozor: WooCommerce posiela kľúče cez HTTP Basic, ktorý funguje len cez HTTPS.
Na `http://` sa autentifikácia tichšie rozbije a vráti 401.
