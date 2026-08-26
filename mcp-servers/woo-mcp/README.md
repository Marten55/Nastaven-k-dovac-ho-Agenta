# woo-mcp

MCP server nad WooCommerce REST API. Vlastná implementácia, nie obal cez tretiu stranu.

## Prečo vlastný server

Univerzálny HTTP MCP server by e-shop obslúžil tiež, ale za cenu kontextu a bezpečnosti:

- WooCommerce vracia na jeden produkt vyše 60 polí. `search_products` ich oreže na 8,
  takže výpis 20 produktov stojí stovky tokenov namiesto tisícov.
- Zápis je za štvorstupňovým režimom, takže sa nedá „omylom naživo".
- `audit_seo` je doménová kontrola, ktorú generický server nevie — vrátane rizikovej
  diakritiky v názvoch (subset fontu bez slovenských mäkčeňov ich zobrazí ako medzeru).
- `set_alt_text` obchádza pascu, na ktorej generický server tichoducho zmaže fotky:
  pole `images` nahradí celú galériu, nie len poslaný obrázok.

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
| `set_alt_text` | alt texty obrázkov bez prepísania galérie, mimo `live` iba náhľad |

### Prečo má alt text vlastný nástroj

WooCommerce pole `images` pri zápise **nahradí celú galériu** tým, čo dostane.
Nie je to čiastočná zmena ako pri ostatných poliach. Kto teda opraví alt text
naivne cez `update_product` a pošle len ten jeden menený obrázok, produktu tým
zmaže všetky ostatné fotky aj ich poradie — a WooCommerce to potvrdí ako úspech.

`set_alt_text` preto galériu najprv načíta, doplní do nej nové alt texty
a pošle ju celú. Zápis navyše odmietne ID obrázka, ktorý k produktu nepatrí
(typicky preklep alebo fotka variantu, ktorá visí na ID variantu), a keď sa
alt text nelíši od súčasného, PUT vôbec neodošle.

`update_product` na `images` upozorní, ale nebráni — galéria sa občas naozaj
vymieňa zámerne.

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

Vo `wc/v3` je variant **podzdroj rodiča** — `products/<id rodiča>/variations/<id>`.
Plochá cesta `products/<id variantu>` nie je pre variant dokumentovaná, takže sa
na ňu server nespolieha. Store API varianty samostatne nevystavuje a vracia ich
na ceste produktu, preto sa v tom režime číta inak.

Keď sa variant načítať nepodarí — alebo keď ich má produkt viac ako 20 — nález sa
zapíše k produktu a celý audit dostane pole `upozornenie`. Ticho vynechaný variant
je horší než hlasná chyba: počet obrázkov by bol nižší než skutočnosť a audit by sa
pritom tváril úplne.

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

48 testov v dvoch súboroch. `test_server.py` beží v režime `fixtures`,
`test_store_mode.py` má zamockované HTTP — ani jeden nepotrebuje e-shop ani sieť.
Pokrývajú okrem iného stránkovanie nad 100 položiek, normalizáciu tvaru zo Store API,
načítanie fotiek variantov, to, že `store` sa nikdy nezavolá s prihlasovacími údajmi,
a že `set_alt_text` pošle celú galériu, nie len menený obrázok.

## Prihlasovacie údaje

WooCommerce → Nastavenia → Pokročilé → REST API → Pridať kľúč. Na audit stačí
oprávnenie *Čítanie*; *Čítanie/Zápis* nasadzuj až keď naozaj zapisuješ. Kľúče idú
do `.env` v koreni repa, ktorý je v `.gitignore`.

Pozor: WooCommerce posiela kľúče cez HTTP Basic, ktorý funguje len cez HTTPS.
Na `http://` sa autentifikácia tichšie rozbije a vráti 401.
