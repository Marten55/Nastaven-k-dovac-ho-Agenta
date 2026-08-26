# Denník rozhodnutí

Prečo je setup postavený takto a čo bola alternatíva.

## 1. Vlastné repo namiesto exportu existujúcej konfigurácie

**Rozhodnutie:** postaviť setup od nuly ako samostatné repo.

**Prečo:** pôvodná konfigurácia bola celá v pluginoch z verejného marketplace —
`~/.claude/agents/`, `skills/` aj `commands/` boli prázdne. Zadanie pluginy aj
marketplace zakazuje, takže export by neodovzdal nič vlastné.

**Dôsledok:** všetko v repe je písané pre tento setup. Nič nie je prevzaté z pluginu.

## 2. Doména e-shopov namiesto generického dema

**Rozhodnutie:** postaviť setup na WooCommerce práci pre slovenských klientov.

**Prečo:** skill má hodnotu len vtedy, keď obsahuje znalosť, ktorú model nemá alebo
si ju musí prácne odvodzovať. Generický „code review" skill je prepis dokumentácie.
Naopak `$e.run` namiesto drag & drop, dvojfázové nastavenie alt textu vo WP REST
alebo to, že 102/2014 je zrušený zákon, sú veci overené praxou.

**Alternatíva:** postaviť to na leadgene, kde MCP server už existoval. Ušetrilo by to
čas na písaní servera, ale odovzdal by sa hotový kód namiesto nového.

## 3. Odstupňované režimy MCP servera namiesto jedného

**Rozhodnutie:** pôvodne `fixtures` / `dry-run` / `live`, default `fixtures`.
Štvrtý režim `store` pribudol neskôr, viď bod 7.

**Prečo:** setup pracuje s e-shopmi, z ktorých klienti žijú. Server, ktorý sa
predvolene spustí v zápisovom režime, je otázka času do prvej nehody. Zároveň to
rieši praktický problém odovzdávky: hodnotiteľ si repo naklonuje a všetko funguje
bez prístupu k akémukoľvek e-shopu.

**Cena:** o niečo viac kódu v klientovi a nutnosť režim všade hlásiť.

## 4. Zápis je v `permissions.ask`, nie v `allow`

**Rozhodnutie:** čítacie MCP nástroje sú predschválené, `update_product`
a `set_alt_text` si vždy pýtajú potvrdenie.

**Prečo:** predschválené čítanie odstráni väčšinu vyskakovacích potvrdení, takže
používateľ prestane klikať „povoliť" automaticky. Potvrdenie potom niečo znamená.

## 5. Hook namiesto ďalšej vety v CLAUDE.md

**Rozhodnutie:** zákaz zápisu do jadra WordPressu je vynútený skriptom.

**Prečo:** inštrukcia v `CLAUDE.md` je text, ktorý sa dá prehliadnuť pri dlhej relácii.
`guard_wp_core.py` beží pred každým `Write`/`Edit` a vráti zamietnutie s návodom, kam
zmena patrí. Má vlastné testy, takže sa vie, že naozaj funguje.

**Cena:** hook musí poznať výnimky (child téma, vlastné ADM pluginy), inak by
blokoval aj legitímnu prácu. Preto tých 10 testovacích prípadov.

## 6. Rôzne modely pre rôznych subagentov

**Rozhodnutie:** `haiku` pre `php-reviewer`, `sonnet` pre editora a copywritera,
`opus` pre audítora.

**Prečo:** kontrola snippetu proti zoznamu vzorov je mechanická práca. Audit, kde
treba zoradiť nálezy podľa dopadu na klienta, nie je. Platiť za opus v oboch
prípadoch je zbytočné.

## 7. Štvrtý režim `store` a čo ho vyvolalo

**Rozhodnutie:** pridať režim `store` — čítanie cez verejné WooCommerce Store API,
bez prihlasovacích údajov.

**Prečo:** pri prvom nasadení na reálny e-shop sa ukázalo, že pôvodné tri režimy
nestačia. Audit treba spraviť najčastejšie skôr, než klient vôbec vygeneruje API
kľúče. Store API je verejné, vracia názov, SKU, krátky popis, kategórie aj alt texty
obrázkov, a zápis cezeň nejde — takže sa v tomto režime nedá nič pokaziť.

**Cena:** Store API má iný tvar odpovede než wc/v3 (ceny v centoch, popisy ako HTML,
iná štruktúra skladu), takže pribudla normalizačná vrstva. Bez nej by každý nástroj
musel vedieť, z ktorého rozhrania dáta prišli.

## 8. Dve ticho nesprávne odpovede, ktoré nasadenie odhalilo

Prvé použitie na katalógu so 127 produktmi ukázalo dve chyby, ktoré nepadali —
len vracali menšie čísla, než je pravda. To je horší druh chyby než výnimka.

1. **Stránkovanie.** WooCommerce zastropuje `per_page` na 100 bez ohľadu na to, čo
   pošleš. Audit teda prešiel prvých 100 produktov a zvyšok ticho vynechal.
2. **Varianty.** Fotka varianty sa na e-shope zobrazí až po prepnutí farby a visí na
   samostatnom objekte. Audit, ktorý pozeral len na rodičovský produkt, ich nevidel —
   na reálnom katalógu išlo o 102 obrázkov navyše.

**Dôsledok pre návrh:** kdekoľvek sa výsledok oreže, vracia sa pole `upozornenie`
a vypnutý rozsah sa hlási v poli `nekontrolovane`. Nástroj, ktorý zamlčí, čo nevidel,
je nebezpečnejší než nástroj, ktorý zlyhá nahlas.

## 9. Alt texty majú vlastný nástroj, nie `update_product`

**Rozhodnutie:** pridať `set_alt_text` ako samostatný ôsmy nástroj.

**Prečo:** WooCommerce pole `images` pri zápise nahradí **celú galériu** tým, čo
dostane — nespráva sa ako čiastočná zmena, hoci každé iné pole áno. Oprava alt textu
poslaná naivne ako `update_product(id, {"images": [{"id": 9101, "alt": "…"}]})`
teda produktu zmaže všetky ostatné fotky aj ich poradie a REST to potvrdí ako
úspešný zápis. To je presne ten druh tichej chyby, ktorý setup rieši od bodu 8.

`set_alt_text` galériu najprv načíta, doplní do nej nové alt texty a pošle ju celú.
Navyše odmietne ID obrázka, ktorý k produktu nepatrí, a keď sa text nelíši od
súčasného, PUT vôbec neodošle.

**Prečo to nebolo hneď:** nástroj bol roky vedený v `permissions.ask` v
`.claude/settings.json` a spomínaný v bode 4 tohto denníka, ale nikdy nebol
napísaný. Konfigurácia teda pýtala potvrdenie na niečo, čo neexistovalo, a audit
síce chýbajúce alt texty našiel, no nemal ich čím opraviť. `overit.py` odvtedy
kontroluje, že každý nástroj spomenutý v konfigurácii je v `server.py` naozaj
zaregistrovaný.

**Cena:** ôsmy nástroj v zozname a jedno čítanie navyše pred každým zápisom altu.

## 10. Overenia beží CI, nie disciplína

**Rozhodnutie:** `.github/workflows/kontrola.yml` spúšťa pri každom pushi tie isté
štyri overenia, aké sú v README, plus testy oboch hookov.

**Prečo:** dovtedy sa spúšťali ručne, takže platili len dovtedy, kým si na ne
niekto spomenul. Obe chyby, ktoré viedli k bodu 9 a k testu `session_context.py`,
sú presne toho typu, čo CI zachytí okamžite a čítanie kódu nie: konfigurácia
odkazovala na nástroj, ktorý neexistoval, a hook nepoznal režim, ktorý medzitým
pribudol do servera. Ani jedna z nich nepadala — obe len ticho nefungovali.

**Cena:** jeden workflow navyše a nutnosť držať README v súlade s tým, čo CI beží.

## 11. Čo sa do setupu zámerne nedostalo

| Vec | Prečo nie |
|---|---|
| MCP server na Gmail/Notion | v repe by boli osobné prístupy klienta |
| Automatické commitovanie a push | agent nemá tlačiť na klientske repo bez kontroly |
| Skill na dizajn a grafiku | nesúvisí s doménou tohto setupu, bola by to vata |
| `tools: *` u ktoréhokoľvek subagenta | zmazalo by to celý zmysel izolácie |
