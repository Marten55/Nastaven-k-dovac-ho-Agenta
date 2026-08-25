---
name: elementor-api
description: Vkladanie a úprava widgetov v Elementor editore cez JavaScript API ($e.run) namiesto drag & drop. Použi, keď treba automatizovane pridať sekciu, widget alebo hromadne upraviť stránku v Elementore. Nepoužívaj na úpravy mimo Elementora ani na WooCommerce produktové dáta.
---

# Elementor cez $e.run

## Prečo nie drag & drop

Elementor stavia plátno v `iframe` a prvky reagujú na vlastnú sekvenciu udalostí.
Simulovaný drag & drop cez automatizáciu prehliadača **nefunguje** — prvok sa buď
nepustí, alebo skončí v nesprávnom kontajneri. Jediná spoľahlivá cesta je príkazové
API editora.

## Základ

Príkazy sa púšťajú v konzole prehliadača, keď je otvorený Elementor editor.
Kód musí bežať v kontexte okna editora, nie v `iframe` plátna.

```js
$e.run('document/elements/create', {
  container: elementor.getPreviewContainer(),
  model: {
    elType: 'widget',
    widgetType: 'heading',
    settings: {
      title: 'Nadpis sekcie',
      header_size: 'h2',
      align: 'center'
    }
  }
});
```

Nastavenia najčastejších widgetov sú v [references/widgety.md](references/widgety.md).

## Poradie krokov

1. Otvor stránku v Elementor editore a počkaj, kým sa načíta plátno.
2. Over, že API je k dispozícii: v konzole musí `typeof $e` vrátiť `object`.
3. Najprv vlož **kontajner**, potom doň widgety — widget bez rodiča skončí na konci
   stránky.
4. Ulož cez `$e.run('document/save/default')`. Bez toho sa zmena stratí pri obnovení.

## Úskalia

- **Zmeny sa nezobrazia** — plátno sa prekresľuje asynchrónne. Medzi vytvorením
  prvku a čítaním jeho stavu nechaj pauzu, nečítaj hodnotu hneď.
- **`$e is not defined`** — kód beží v iframe plátna. Prepni kontext na hlavné okno.
- **Widget sa vloží, ale bez štýlov** — chýbajú `settings`. Elementor dopĺňa
  predvolené hodnoty len pri vložení cez UI, nie cez API.
- **Uloženie prepíše cudziu prácu** — ak má stránku otvorenú aj klient, posledné
  uloženie vyhrá. Pred hromadnou úpravou to over.
- **Neexistujúci `widgetType` zlyhá potichu** — over názov widgetu v paneli editora,
  nie podľa dokumentácie; názvy sa medzi verziami menili.

## Bezpečnosť

Toto je zásah do živej stránky. Pred úpravou si vyžiadaj potvrdenie a odporuč
klientovi zálohu, prípadne pracuj na koncepte stránky, nie na publikovanej verzii.
