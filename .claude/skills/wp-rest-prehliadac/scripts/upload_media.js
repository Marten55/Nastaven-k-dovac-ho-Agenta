/**
 * Nahratie fotky do WordPress knižnice médií z konzoly prehliadača.
 *
 * Spustiť v prihlásenej admin relácii, na rovnakej doméne ako e-shop.
 * Fotku načíta cez canvas a odošle ako Blob - base64 WordPress odmieta.
 *
 * Použitie:
 *   const id = await nahrajFotku('https://zdroj.sk/foto.jpg', 'foto-produktu.jpg',
 *                                'Predné brzdové doštičky pre štvorkolku XB48');
 */

async function ziskajNonce() {
  return fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
    credentials: 'same-origin'
  }).then(r => r.text());
}

async function urlNaBlob(url) {
  const obrazok = await new Promise((vyries, zamietni) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => vyries(img);
    img.onerror = () => zamietni(new Error('Fotku sa nepodarilo načítať: ' + url));
    img.src = url;
  });

  const canvas = document.createElement('canvas');
  canvas.width = obrazok.naturalWidth;
  canvas.height = obrazok.naturalHeight;
  canvas.getContext('2d').drawImage(obrazok, 0, 0);

  return new Promise(vyries => canvas.toBlob(vyries, 'image/jpeg', 0.9));
}

async function nahrajFotku(zdrojUrl, nazovSuboru, altText) {
  const nonce = await ziskajNonce();
  const blob = await urlNaBlob(zdrojUrl);

  const formular = new FormData();
  formular.append('file', blob, nazovSuboru);

  const nahrate = await fetch('/wp-json/wp/v2/media', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-WP-Nonce': nonce },
    body: formular
  }).then(r => r.json());

  if (!nahrate.id) {
    throw new Error('Nahratie zlyhalo: ' + JSON.stringify(nahrate));
  }

  // Alt text sa pri nahrávaní ignoruje, treba druhé volanie.
  if (altText) {
    await fetch('/wp-json/wp/v2/media/' + nahrate.id, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
      body: JSON.stringify({ alt_text: altText })
    });
  }

  console.log('Nahraté ID ' + nahrate.id + ': ' + nahrate.source_url);
  return nahrate.id;
}

/**
 * Dávkové nahratie. Medzi fotkami necháva pauzu, aby hosting nevrátil 429.
 * polozky = [{ url, nazov, alt }, ...]
 */
async function nahrajDavku(polozky, pauzaMs = 1200) {
  const vysledky = [];
  for (const [i, p] of polozky.entries()) {
    try {
      const id = await nahrajFotku(p.url, p.nazov, p.alt);
      vysledky.push({ ...p, id, stav: 'OK' });
    } catch (chyba) {
      console.warn('Zlyhalo: ' + p.nazov, chyba);
      vysledky.push({ ...p, id: null, stav: 'CHYBA', detail: String(chyba) });
    }
    if (i < polozky.length - 1) {
      await new Promise(r => setTimeout(r, pauzaMs));
    }
  }
  console.table(vysledky);
  return vysledky;
}
