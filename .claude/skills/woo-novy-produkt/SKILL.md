---
name: woo-novy-produkt
description: Pridanie alebo úprava produktu vo WooCommerce e-shope pre slovenského klienta — názvy, SKU, varianty, kategórie, alt texty, sklad a cena. Použi, keď používateľ chce nahrať produkt, opraviť existujúci, zlúčiť varianty alebo hromadne doplniť alt texty. Nepoužívaj na úpravy vzhľadu šablóny ani na Elementor.
---

# Nový produkt vo WooCommerce

## Poradie krokov

Nikdy nezačínaj zápisom. Vždy najprv:

1. `mcp__woo__server_status` — over režim. V `fixtures` sú dáta demo, v `live` každý
   zápis mení ostrý e-shop.
2. `mcp__woo__search_products` s SKU alebo časťou názvu — over, či produkt už
   neexistuje. Duplicitné SKU je najčastejšia chyba pri hromadnom nahrávaní.
3. Priprav zmenu a ukáž ju používateľovi ako náhľad.
4. Zapíš cez `mcp__woo__update_product`.

## Povinné polia

| Pole | Pravidlo |
|---|---|
| `name` | do 70 znakov, inak sa v Google oreže; formát „Čo to je + model + parameter" |
| `sku` | konvencia `<SKUPINA>-<ČÍSLO>`, napr. `XB47-0012`; SKU bez čísla je podozrivé |
| `short_description` | 1–2 vety, povinné — bez neho je produkt slabý v kategórii aj vo vyhľadávaní |
| `regular_price` | s DPH, desatinná bodka, bez symbolu meny |
| `categories` | aspoň jedna; nové kategórie zakladaj až po dohode s klientom |
| `images[].alt` | povinné pre každý obrázok, viď nižšie |

## Alt texty

Alt text nie je názov súboru ani zopakovaný názov produktu. Napíš, čo je na fotke
vrátane pohľadu: „Predné brzdové doštičky pre štvorkolku XB48, pohľad zhora".

Diakritika: **skontroluj, či font na webe vykresľuje Š, Č, Ť, Ľ, Ž**. Subset fontu
z Adobe web kitu ich často neobsahuje a na webe sa zobrazia ako prázdne miesto.
`mcp__woo__audit_seo` na to upozorní, ale rozhodnutie je vizuálne — over v prehliadači.

## Varianty

Zlučovanie samostatných produktov do variantov je nezvratné a rozbíja odkazy.
Detailný postup vrátane presmerovaní: [references/varianty.md](references/varianty.md).

## Sklad a backorders

Pri `stock_status: onbackorder` vždy nastav aj `backorders` (`notify` alebo `yes`) —
inak WooCommerce položku síce označí, ale nedovolí ju objednať a klient hlási „nedá sa
kúpiť". Kontrola: `mcp__woo__check_stock`.

## Hromadné zmeny

Nad 20 produktov si vyžiadaj potvrdenie a najprv spusti s `WOO_MODE=dry-run`. Skript na
prípravu dávky z CSV: [scripts/priprav_davku.py](scripts/priprav_davku.py).
