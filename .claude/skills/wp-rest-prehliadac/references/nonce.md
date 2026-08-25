# Získanie REST nonce vo WordPresse

## Spôsob 1 — admin-ajax (najspoľahlivejší)

```js
const nonce = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
  credentials: 'same-origin'
}).then(r => r.text());
```

Funguje na ktorejkoľvek obrazovke admina. Akcia `rest-nonce` je súčasťou jadra
WordPressu, netreba plugin.

## Spôsob 2 — globálna premenná

```js
const nonce = window.wpApiSettings && wpApiSettings.nonce;
```

Existuje len ak sa na stránke načítal skript `wp-api-request`. Na mnohých obrazovkách
admina tam nie je. Použi ako doplnok, nie ako hlavný spôsob.

## Spôsob 3 — Gutenberg

```js
const nonce = window.wp && wp.apiFetch && wp.apiFetch.nonceMiddleware
  && wp.apiFetch.nonceMiddleware.nonce;
```

Dostupné v editore príspevkov. Mimo editora nie.

## Overenie, že nonce funguje

```js
const test = await fetch('/wp-json/wp/v2/users/me', {
  credentials: 'same-origin',
  headers: { 'X-WP-Nonce': nonce }
}).then(r => r.json());
console.log(test.name, test.capabilities ? 'prava OK' : 'bez prav');
```

Ak vráti `rest_not_logged_in`, relácia nie je prihlásená. Ak vráti
`rest_cookie_invalid_nonce`, nonce je zlý alebo vypršaný.

## Životnosť

Nonce vo WordPresse platí v dvoch dlaždiciach po 12 hodinách. Prakticky teda platí
12 až 24 hodín, ale spoliehať sa na to nemožno. Pri dlhšej dávke si ho obnov.

## Prečo nie API kľúče

WooCommerce REST kľúče sa posielajú cez HTTP Basic a fungujú len cez HTTPS. Ak
klient beží na `http://`, autentifikácia zlyhá na 401 bez zrozumiteľnej hlášky.
V takom prípade je cookie + nonce jediná fungujúca cesta, kým sa nenasadí certifikát.
