# Šablóna odovzdávacieho dokumentu

Skopíruj obsah bloku nižšie a vypĺňaj hranaté zátvorky.

~~~markdown
# [Názov projektu] — [zadanie | priebežný report | odovzdávka]

**Dátum:** [DD. MM. RRRR]
**Klient:** [meno / firma]
**Za ADM Technics:** Martin Mutka

## 1. Zadanie

1. [prvý bod zadania]
2. [druhý bod zadania]
3. [tretí bod zadania]

## 2. Čo je hotové

| # | Položka | Stav | Poznámka |
|---|---|---|---|
| 1 | [popis] | hotové | [odkaz alebo detail] |
| 2 | [popis] | hotové | |

## 3. Čo zostáva

### Čaká sa na klienta
- [ ] **[položka]** — čaká sa na: [čo presne treba dodať]
      *bez toho sa nedá pokračovať v: [nadväzujúca úloha]*

### Na strane ADM Technics
- [ ] **[položka]** — predpokladaný termín: [dátum]

### Automatizované / agent
- [ ] **[položka]** — spustí sa po: [podmienka]

## 4. Náklady

| Položka | Cena | Periodicita | Platí |
|---|---|---|---|
| [doména] | [XX €] | ročne | klient |
| [licencia pluginu] | [XX €] | ročne | klient |
| [práce] | [XX €] | jednorazovo | klient |
| **Spolu prvý rok** | **[XX €]** | | |

## 5. Prístupy

Prístupové údaje boli odovzdané samostatným kanálom. V tomto dokumente sa neuvádzajú.

## 6. Ďalší krok

[Jedna veta: čo sa stane ako ďalšie a kto to začne.]
~~~

## Poznámky k vypĺňaniu

- Sekciu „Čaká sa na klienta" nevynechávaj, ani keď je prázdna — napíš „nič,
  všetko potrebné je dodané". Klient tak vidí, že sa naňho nečaká.
- Ak je nákladov málo, tabuľku nahraď vetou s číslom. Nikdy ju nevynechaj úplne.
- Pri odovzdávke pridaj sekciu „Čo si klient vie zmeniť sám" s krátkym návodom —
  ušetrí to neskoršie otázky.
- Dokument ukladaj ako `zadanie-<klient>.md`, `report-<klient>.md` alebo
  `zostava-<klient>.md`, aby sa dal neskôr nájsť podľa fázy projektu.
