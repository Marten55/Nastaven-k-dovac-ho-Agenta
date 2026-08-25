---
description: Prevedie pridaním produktu do WooCommerce od kontroly duplicity po zápis a alt texty
argument-hint: [SKU alebo názov produktu]
allowed-tools: Skill, Task, Read, mcp__woo__server_status, mcp__woo__search_products, mcp__woo__get_product, mcp__woo__check_stock
---

Pridaj produkt: **$ARGUMENTS**

Použi skill `woo-novy-produkt` a drž sa jeho poradia krokov.

1. Over režim cez `mcp__woo__server_status`.
2. Skontroluj duplicitu cez `mcp__woo__search_products` — hľadaj podľa SKU aj názvu.
3. Zisti od používateľa, čo chýba z povinných polí. Pýtaj sa naraz, nie po jednom.
4. Texty (názov, krátky a dlhý popis, alt texty) nechaj napísať subagentovi
   `sk-copywriter`.
5. Ukáž kompletný náhľad produktu a vyžiadaj si potvrdenie.
6. Zápis deleguj subagentovi `woo-data-editor`.

Ak je režim `fixtures` alebo `dry-run`, na konci jasne napíš, že produkt sa
nezapísal a čaká na prepnutie do `live`.
