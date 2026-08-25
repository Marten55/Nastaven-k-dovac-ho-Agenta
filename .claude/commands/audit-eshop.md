---
description: Spustí kompletný audit e-shopu cez subagenta eshop-auditor a vráti nálezy podľa priority
argument-hint: [oblasť: seo | pravne | sklad | vsetko]
allowed-tools: Task, mcp__woo__server_status
---

Spusti audit e-shopu.

Rozsah: **$1** (ak je prázdny, audituj všetko).

Postup:

1. Zavolaj `mcp__woo__server_status` a zisti režim.
2. Deleguj audit subagentovi `eshop-auditor`. Odovzdaj mu rozsah aj zistený režim.
3. Report od subagenta odovzdaj používateľovi **bez skracovania** — tabuľku nálezov
   ani sekciu „Čo som nekontroloval" nevynechávaj.
4. Na záver pridaj jednu vetu: čo by som opravil ako prvé a prečo.

Nespúšťaj žiadne opravy. Tento príkaz iba zisťuje stav.
