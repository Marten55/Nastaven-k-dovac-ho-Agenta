---
description: Spíše odovzdávací dokument pre klienta vo formáte ADM Technics
argument-hint: [meno klienta] [zadanie | report | odovzdavka]
allowed-tools: Skill, Read, Grep, Glob, Write
---

Priprav dokument pre klienta: **$1**, typ: **$2**.

Použi skill `klient-report` a jeho šablónu.

1. Prejdi súbory projektu a zisti, čo je hotové. Nehádaj — čo nevieš overiť, uveď
   ako otázku pre používateľa v samostatnej sekcii na konci.
2. Vyplň šablónu. Sekciu „Čaká sa na klienta" nikdy nevynechaj.
3. Ceny doplň konkrétnymi číslami. Ak ich nemáš, označ ich `[DOPLNIŤ: …]` a vypíš
   ich na konci ako zoznam toho, čo treba zistiť.
4. Ulož ako `$2-$1.md` v koreni projektu.

Do dokumentu nikdy nepíš prihlasovacie údaje ani reálne domény klientov, ak ide
o ukážkový výstup.
