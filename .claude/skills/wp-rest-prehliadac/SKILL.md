---
name: wp-rest-prehliadac
description: Úpravy WordPressu cez REST API priamo z konzoly prehliadača v prihlásenej admin relácii — získanie nonce, zápis produktov a stránok, nahrávanie fotiek do knižnice médií. Použi, keď nie sú k dispozícii API kľúče, alebo keď treba jednorazovú hromadnú zmenu bez inštalácie pluginu. Nepoužívaj, keď je dostupný woo MCP server — ten je bezpečnejší.
---

# WordPress REST z prehliadača

## Kedy to použiť

Až keď nie je lepšia cesta. Poradie preferencií:

1. `woo` MCP server — má režimy a náhľad zmien.
2. WP-CLI, ak máš SSH prístup.
3. Tento postup — jednorazová zmena v prihlásenej admin relácii.

Nikdy to nepoužívaj na opakovanú automatizáciu. Nonce vyprší a relácia je viazaná
na prihláseného používateľa, takže výsledok nie je reprodukovateľný.

## Nonce

REST API vyžaduje `X-WP-Nonce`. Na stránke admina býva v `wpApiSettings.nonce`,
ale nie je tam vždy — závisí od toho, ktoré skripty sa na danej obrazovke načítali.

Spoľahlivejšie je vypýtať si ho cez `admin-ajax.php`:

```js
const nonce = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
  credentials: 'same-origin'
}).then(r => r.text());
```

Detaily a záložné spôsoby: [references/nonce.md](references/nonce.md)

## Zápis

```js
await fetch('/wp-json/wc/v3/products/101', {
  method: 'POST',
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
  body: JSON.stringify({ short_description: 'Nový krátky popis.' })
});
```

Cookie autentifikácia funguje len pre **rovnaký pôvod**. Volanie z inej domény zlyhá
na 401 aj so správnym nonce.

## Nahrávanie fotiek

Fotku neposielaj ako base64 — WordPress ju odmietne alebo uloží poškodenú. Načítaj ju
do `canvas` a odošli ako `Blob` cez `FormData`. Hotový skript:
[scripts/upload_media.js](scripts/upload_media.js)

Alt text sa nastavuje až **druhým** volaním na `/wp-json/wp/v2/media/<id>` s poľom
`alt_text`. Pri nahrávaní sa ignoruje.

## Úskalia

- **403 s `rest_cookie_invalid_nonce`** — nonce vypršal (platí rádovo hodiny).
  Vypýtaj si nový, nepoužívaj starý z predchádzajúcej relácie.
- **Zmena sa zapíše, ale nezobrazí** — cache pluginu alebo CDN. Preplachni cache,
  než začneš hľadať chybu v kóde.
- **Wholesale ceny sa neprepíšu** — pluginy veľkoobchodných cien držia hodnoty
  v metadátach, nie v štandardných poliach produktu. Zapisuj cez `meta_data`.
- **Backorders** — nastavenie `stock_status: onbackorder` bez `backorders` spôsobí,
  že produkt sa tvári dostupný, ale nedá sa objednať.
- **Hromadné volania** — medzi requestmi nechaj pauzu. Bez nej hosting vráti 429
  alebo spadne PHP worker.

## Bezpečnosť

Toto beží v prihlásenej relácii s právami daného používateľa. Pred hromadnou zmenou:

1. Vyžiadaj si potvrdenie od používateľa.
2. Najprv spusti verziu, ktorá iba číta a vypíše, čo by sa zmenilo.
3. Odporuč zálohu databázy.
