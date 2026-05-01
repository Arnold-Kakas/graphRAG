# GraphRAG Explorer — Sprievodný text k prezentácii

---

## Úvod

Vitajte. Dnes vám ukážem aplikáciu GraphRAG Explorer — nástroj, ktorý dokáže premeniť hromadu dokumentov na interaktívny znalostný graf a chatovateľnú znalostnú bázu.

Celý princíp je jednoduchý: hodíte dnu PDF-ká, Word dokumenty, webové stránky, tabuľky alebo čistý text, vyberiete jazykový model a aplikácia za vás extrahuje entity, vzťahy medzi nimi a zoskupí ich do tematických komunít. Výsledok potom môžete preskúmavať cez interaktívny graf, pýtať sa otázky v chate, generovať blog príspevky alebo exportovať celú znalostnú bázu do Obsidianu.

Aplikácia funguje buď lokálne — teda žiadne vaše dáta neopustia váš počítač — alebo cez cloudové API ako OpenAI, Anthropic alebo Google Gemini. Záleží len na vás.

---

## Čo je na obrazovke

Keď aplikáciu prvýkrát otvoríte, uvidíte tri hlavné časti.

Vľavo je chatovací panel — tam budete klásť otázky o vašich dokumentoch.

Uprostred je samotný graf — vizualizácia všetkých entít a vzťahov, ktoré aplikácia extrahovala z vašich dokumentov.

Vpravo sa zobrazí panel s detailmi vždy, keď kliknete na niektorý uzol alebo hranu v grafe.

Hore v hlavičke vidíte rozbaľovacie menu na výber témy, tlačidlá na budovanie grafu a zlučovanie entít a vpravo indikátor aktívneho jazykového modelu.

---

## Témy a dokumenty

Aplikácia organizuje dokumenty do tém. Každá téma je samostatný priečinok v adresári `raw/` na vašom počítači — názov priečinka sa automaticky stane názvom témy v aplikácii.

My sme si na dnešnú ukážku pripravili projekt o Marketing Mix Modelingu. Do priečinka sme nahrali niekoľko PDF štúdií a článkov na túto tému. Vyberte si tému z rozbaľovacieho menu — a tu ju vidíte.

Podporované formáty sú PDF, Word, HTML, čistý text, Markdown aj CSV. Dokumenty môžete pridávať kedykoľvek za chodu — nie je potrebný reštart aplikácie ani kontajnera.

---

## Budovanie grafu

Teraz kliknem na **Build Graph**.

Pred samotným budovaním sa objaví okno, kde môžete aplikácii povedať, čo vás v dokumentoch zaujíma najviac. Napríklad: zameraj sa na marketingové kanály, meranie ROI a alokáciu rozpočtu. Táto inštrukcia sa použije pri extrakcii a ovplyvní, na čo si model dá pozor.

Ak používate uvažovací model — napríklad DeepSeek R1 alebo QwQ — zaškrtnite políčko Reasoning model. Tieto modely generujú dlhý reťazec myšlienok pred finálnou odpoveďou a bez tohto nastavenia by sa extrakcia mohla zacykliť.

Klikneme na Build Graph a sledujeme stavový riadok v spodnej časti obrazovky.

Aplikácia prechádza dokumentmi paralelne — na každý dokument vykoná dve LLM volania. Prvé skomprimuje dokument do súhrnu, druhé z neho extrahuje entity a vzťahy. Potom prebehne detekcia komunít — zhlukuje entity do tematických skupín — a pre každú skupinu vygeneruje súhrnný popis.

Keď budovanie skončí, v stavovom riadku uvidíte počet uzlov, hrán a komunít. A v grafe sa objaví celá sieť.

---

## Preskúmavanie grafu

Pozrite sa na graf. Každý uzol je jedna entita — koncept, organizácia, metóda alebo akýkoľvek iný typ objektu, ktorý model v dokumentoch našiel. Veľkosť uzla zodpovedá jeho stupňu — čím viac spojení má, tým väčší je. Farba označuje typ entity — legenda je v bočnom paneli vľavo.

Graf môžete posúvať ťahaním pozadia, priblížiť kolieskom myši a jednotlivé uzly presúvať ťahaním.

V bočnom paneli máte posuvníky na nastavenie vzdialenosti hrán a hustoty uzlov — ak je graf príliš preplnený, trochu ich ponastavujte.

### Vyhľadávanie

Vo vyhľadávacom poli začnem písať — napríklad „ROAS". Výsledky sa radia podľa kvality zhody, nie len abecedne. Najprv presné zhody v názve, potom čiastočné, potom zhody v type alebo popise. Vedľa každého výsledku vidíte stupeň uzla a ID zhluku — teda do akej komunity patrí.

### Detail uzla

Kliknem na uzol — napríklad na Marketing Mix Modeling. Na pravej strane sa vysunie panel s detailmi. Vidíte tu popis entity, zo ktorých zdrojových dokumentov bola extrahovaná, do akej komunity patrí a všetky vzťahy — kde je táto entita zdrojom a kde je cieľom.

### Wiki článok

Teraz dvakrát kliknem na rovnaký uzol. Aplikácia vygeneruje Wikipedia-štýlový článok o tejto entite — tri až päť odsekov syntetizovaných z jej popisu, vzťahov a súhrnu komunity, ku ktorej patrí. Článok sa po prvom vygenerovaní uloží, takže pri ďalšom dvojitom kliknutí sa načíta okamžite.

---

## Zlučovanie entít

Po budovaní sa v grafe často objaví niekoľko takmer duplicitných uzlov. Napríklad „Marketing Mix Modeling" a „Marketing Mix Model" sú v podstate to isté.

Klikneme na **Merge entities** v hlavičke.

Aplikácia najprv spustí pravidlové normalizovanie — automaticky zachytí pravopisné varianty, swapy gerundia a podstatného mena, rozvinutia skratiek. Potom spustí jeden alebo dva LLM prechody na nájdenie sémantických synoným, ktoré pravidlá nestačili zachytiť.

Výsledky sa uložia do súboru `learned_aliases.json`. Od tohto momentu sa pri každom ďalšom budovaní tieto aliasy automaticky aplikujú zadarmo — LLM zaplatí náklady na rozlíšenie iba raz.

Zlúčenie je zámerné oddelené od budovania — môžete si najprv pozrieť surový graf, až potom sa rozhodnúť, či chcete mergovať.

---

## Chat — kladenie otázok

Teraz si ukážeme chatovací panel.

Mám tu dve možnosti — prepínač v spodnej časti panela:

**Graph only** — model odpovedá striktne na základe toho, čo je v grafe. Ak odpoveď v grafe nie je, povie to. Vety, ktoré nie sú podložené dôkazmi z grafu, sa automaticky odfiltrácia.

**Graph + AI knowledge** — model môže doplniť vlastnými tréningovými znalosťami. Výsledok je rozdelený na dve sekcie: čo pochádza z grafu a čo z modelu samotného.

Napíšem otázku — napríklad: „Aké sú hlavné faktory ovplyvňujúce návratnosť investícií v marketingu?"

Sledujte, ako odpoveď prichádza po tokenoch priamo v reálnom čase. V texte odpovede si všimnete modré čipy s názvami entít — to sú klikateľné odkazy priamo do grafu. Keď na jeden kliknem, graf sa posunie k danému uzlu a zvýrazní ho.

Pod odpoveďou vidíte, ktoré komunitné zhluky k nej prispeli. Rozbalím jeden — a tu je celý súhrn komunity, z ktorého model čerpal.

Ak je odpoveď užitočná, môžem ju pripnúť ikonou špendlíka. Pripnuté odpovede sa uložia do bočného panela a pretrvajú aj po obnovení stránky.

---

## Generovanie blog príspevku

Teraz ukážem jednu z mojich obľúbených funkcií — generátor blog príspevkov.

V bočnom paneli pod sekciou Export kliknem na **Write Blog Post**.

Otvorí sa okno, kde zadám:
- Môj uhol a nápady — napríklad: „Chcem vysvetliť, prečo je Marketing Mix Modeling dôležitý pre moderné firmy a aké sú jeho praktické výhody oproti last-click atribúcii."
- Volitelnú osnovu — môžem napísať hrubú štruktúru článku, alebo nechám model rozhodnúť sám.
- Cieľovú dĺžku — Short okolo 500 slov, Medium okolo 1 000, Long okolo 1 800.

Kliknem na **Generate Blog Post**.

Príspevok sa začne streamovať priamo v celoobrazovkovom náhľade. Model čerpá z dvadsiatich najrelevantnejších komunitných súhrnov, tridsiatich najcentrálnejších entít a štyridsiatich vzťahov z grafu — plus číslovaný zoznam zdrojových dokumentov ako podklady pre citácie.

Ak model vygeneruje chart blok, renderuje sa ako interaktívny Chart.js graf priamo v náhľade.

Citácie zdrojov vidíte ako superscript čísla — každé odkazuje na pôvodný dokument zo zoznamu referencií na konci príspevku.

Keď je príspevok hotový, mám dve možnosti exportu:

**Export MD** stiahne surový Markdown — môžem ho upraviť v akomkoľvek editore.

**Export HTML** vygeneruje samostatný HTML súbor s interaktívnymi grafmi, inline skriptami a CSS. Ten môžem priamo nahrať do WordPressu, Ghostu, Substack alebo akéhokoľvek iného CMS.


---

## Nastavenia modelu

Naposled ukážem nastavenia. Kliknem na ozubené koliesko vpravo hore.

Tu môžete zmeniť poskytovateľa — OpenAI, Anthropic, Gemini, LM Studio, Ollama alebo vlastný OpenAI-kompatibilný endpoint. Zadáte API kľúč, základnú URL a názvy modelov pre extrakciu a dotazy.

Tieto nastavenia sa uložia iba v sessionStorage prehliadača — nikdy sa nezapíšu na disk a automaticky sa vymažú, keď zatvoríte záložku. V navigačnej lište vždy vidíte, ktorý model je aktívny.

To je užitočné napríklad vtedy, keď chcete dočasne vyskúšať iný model bez toho, aby ste menili konfiguráciu servera.

---

## Záver

Celé riešenie beží lokálne cez Docker, takže vaše dáta zostanú tam, kde majú byť — u vás. Ak máte záujem, kód je voľne dostupný a môžete ho nasadiť na vlastnom serveri alebo ho jednoducho spustiť na laptope.

Ďakujem za pozornosť.
