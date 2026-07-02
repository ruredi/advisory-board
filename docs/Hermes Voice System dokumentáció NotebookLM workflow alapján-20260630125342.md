# Hermes Voice System dokumentáció NotebookLM workflow alapján

# Hermes Voice System dokumentáció NotebookLM workflow alapján
## 1\. Cél
A cél egy olyan Hermes persona profile létrehozása, amely képes egy adott személy kommunikációs stílusát követni fine tuning nélkül.
Nem csak azt akarjuk elérni, hogy a modell hasonló szavakat használjon, hanem azt is, hogy hasonló módon gondolkodjon, strukturáljon, kritizáljon, egyszerűsítsen és fogalmazzon.
A rendszer két külön kommunikációs profilt kezel:
1. Írott stílus
2. Beszélt stílus
Az írott stílus nem lehet túl steril vagy ChatGPT szagú, de nem is lehet teljesen beszédszerűen széteső.
A beszélt stílus természetesebb, tartalmazhat töltelékszavakat, ismétléseket, önjavításokat és gondolkodási ritmust.
## 2\. Alapelv
Nem egyetlen hosszú promptot építünk, hanem egy strukturált persona rendszert.
A NotebookLM szerepe:
1. Források feldolgozása
2. Írott és beszélt stílus külön elemzése
3. Visszatérő minták felismerése
4. Jó és rossz példák kivonása
5. Hermes profile fájlok előállítása
A Hermes szerepe:
1. Persona profile betöltése
2. Output mód kiválasztása
3. Írott vagy beszélt stílus alkalmazása
4. Példák és szabályok alapján válasz generálása
## 3\. Fontos döntések
### 3.1 Egy NotebookLM notebook használata
Az írott, hang és videó alapanyagok mehetnek egy NotebookLM notebookba.
Ennek oka, hogy egy notebookon belül a rendszer látja a teljes kommunikációs univerzumot, de a promptban egyértelműen megmondjuk neki, hogy az írott és beszélt stílust külön kezelje.
### 3.2 Írott stílus forrásai
Az írott stílust csak írott anyagokból elemezze.
Példák:
1. Chat üzenetek
2. Email válaszok
3. Kommentek
4. Social media posztok
5. Dokumentumok
6. Jóváhagyott AI válaszok
7. Átírt szövegek
8. Korábbi promptok
9. Üzleti és stratégiai jegyzetek
Kivétel: ha egy írott dokumentumban egyértelműen fel van tüntetve, hogy az pontos idézet egy beszédből, voice note-ból, podcastból, videóból vagy hívásból, akkor azt beszélt stílusmintaként kell kezelni.
### 3.3 Beszélt stílus forrásai
A beszélt stílust csak természetes beszédből elemezze.
Példák:
1. Voice note
2. Podcast
3. Meeting felvétel
4. Természetes videóbeszéd
5. Hívásrészlet
6. Természetes beszédből készült pontos transzkript
### 3.4 Mit nem használunk beszélt stílusmintának
Nem töltünk fel vagy nem használunk beszélt stílusmintaként olyan hang vagy videó anyagot, ahol csak egy előre megírt szöveg van felolvasva.
Ez nem természetes beszédstílus, hanem írott stílus audio formában.
Ilyen anyag legfeljebb külön kategóriában használható, például scriptelt vagy felolvasott anyagként, de nem szabad a természetes beszédstílus alapjába keverni.
## 4\. Forrás előkészítési szabályok
A forrásokat nem kötelező túladminisztrálni, de érdemes minimális címkézést használni, hogy a NotebookLM ne mossa össze a kategóriákat.
Javasolt címkék a fájlnevekben:
1. WRITTEN
2. SPOKEN\_NATURAL
3. SPOKEN\_TRANSCRIPT
4. SCRIPTED\_AUDIO
5. BAD\_AI\_EXAMPLE
6. APPROVED\_EXAMPLE
Példák:

```plain
WRITTEN_chat_rewrites_approved.md
WRITTEN_social_posts_approved.md
WRITTEN_business_strategy_notes.md
SPOKEN_NATURAL_voice_notes_product_feedback.mp3
SPOKEN_TRANSCRIPT_meeting_strategy.docx
SCRIPTED_AUDIO_promo_video_readout.mp3
BAD_AI_EXAMPLE_generic_answers.md
APPROVED_EXAMPLE_best_persona_style_answers.md
```

A címkézés célja nem az, hogy a rendszer enélkül ne értené meg, hanem az, hogy kisebb legyen az összemosás esélye.
## 5\. Feltöltendő alapanyagok
### 5.1 Írott anyagok
Minimum ajánlott mennyiség:
1. 30 darab természetes chat vagy üzenet
2. 20 darab komment vagy social poszt
3. 10 darab email vagy üzleti válasz
4. 10 darab stratégiai vagy product feedback
5. 10 darab design feedback
6. 10 darab jóváhagyott AI válasz
7. 10 darab elutasított, rossz AI válasz
### 5.2 Beszélt anyagok
Minimum ajánlott mennyiség:
1. 10 darab voice note
2. 3 darab hosszabb meeting vagy beszélgetés részlet
3. 3 darab természetes videó vagy podcast részlet
4. 5 darab olyan részlet, ahol a célszemély spontán kritizál, dönt vagy magyaráz
### 5.3 Kifejezetten fontos minták
A legértékesebb anyagok azok, ahol nem előadás történik, hanem természetes gondolkodás.
Különösen hasznos:
1. Amikor a célszemély valamit javít
2. Amikor valamit túl AI szagúnak tart
3. Amikor egy üzleti ötletet bont szét
4. Amikor design feedbacket ad
5. Amikor egy üzenetet természetesebbre ír át
6. Amikor vitázik vagy ellenérvet mond
7. Amikor egy döntési helyzetben priorizál
## 6\. Forráskereső prompt NotebookLM-hez
Ezt a promptot akkor használjuk, amikor további forrásokat akarunk keresni a NotebookLM keresőjével egy adott célszemélyhez.
A cél az, hogy ne általános róla szóló cikkeket gyűjtsünk, hanem olyan forrásokat, ahol a célszemély saját hangján ír vagy beszél.

```verilog
Person: {NAME}

Find sources where this person speaks or writes in their own voice: interviews, podcasts, keynotes, speeches, earnings or shareholder Q&A, signed essays, founder letters, and their own social posts.

Prioritize full transcripts and original recordings with direct quotes.

Include the company's mission, vision, and philosophy ONLY when this person personally states or writes it, for example in a signed manifesto, a keynote they deliver, or an interview where they explain it.

Exclude:
1. Institutional or PR copy authored by "the team" with no personal byline
2. Generic corporate mission pages in "we" voice
3. Articles that are about this person but do not quote them
4. Third-party summaries of what they think
5. Analyst pieces about their companies where they do not speak

Goal:
Capture this person's actual written and spoken style for persona analysis.
```

### 6.1 Használati szabály
A `{NAME}` helyére a célszemély nevét kell írni.
Példa:

```yaml
Person: Steve Jobs
```

vagy

```yaml
Person: Elon Musk
```

A találatokat csak akkor érdemes felvenni a NotebookLM forrásai közé, ha ténylegesen tartalmaznak saját hangú kommunikációt.
### 6.2 Legjobb forrástípusok
1. Teljes interjú transcript
2. Teljes podcast transcript
3. Keynote videó vagy transcript
4. Részvényesi Q&A
5. Founder letter
6. Saját név alatt publikált esszé
7. Saját social media poszt
8. Olyan céges filozófia vagy manifesto, amit bizonyíthatóan a célszemély írt vagy mondott
### 6.3 Kerülendő források
1. Róla szóló portrécikk, ha nincs benne elég direkt idézet
2. PR anyag személyes byline nélkül
3. Céges About us vagy mission oldal, ha intézményi többes számban íródott
4. Harmadik fél által írt összefoglaló
5. Elemzői cikk
6. Olyan könyvrészlet vagy cikk, amely csak értelmezi a gondolkodását, de nem idézi közvetlenül
Ez azért fontos, mert a persona elemzéshez nem az kell, hogy mások mit gondolnak róla, hanem az, hogy ő hogyan fogalmaz, hogyan strukturál, milyen ritmust használ, hogyan érvel, hogyan mond nemet, hogyan magyaráz és hogyan reagál.
## 7\. NotebookLM master prompt
Ezt a promptot kell használni a NotebookLM-ben a források feldolgozásához.

```markdown
Feladatod egy Hermes persona profile előkészítése egy adott célszemély kommunikációs stílusa alapján.

Ne tartalmi összefoglalót készíts. Ne azt mondd el, miről szólnak a források. A kommunikációs stílust, gondolkodási mintákat, szóhasználatot, válaszszerkezetet, tiltott mintákat és jó példákat elemezd.

Két külön kommunikációs csatornát kezelj:

1. Írott stílus

Az írott stílust kizárólag írott anyagokból elemezd, például chat üzenetekből, emailből, kommentekből, social posztokból, dokumentumokból, jóváhagyott írott válaszokból és korábbi írott promptokból.

Kivétel: ha egy írott dokumentumban egyértelműen fel van tüntetve, hogy az pontos idézet egy beszédből, voice note-ból, podcastból, videóból vagy hívásból, akkor azt ne írott stílusmintaként kezeld, hanem beszélt stílusmintaként.

2. Beszélt stílus

A beszélt stílust kizárólag természetes beszédből elemezd, például hangfelvételekből, voice note-okból, podcastokból, videókból, meetingekből, hívásokból vagy ezek pontos transzkriptjeiből.

Fontos kizárás:

Ne használj olyan hang vagy videó anyagot beszélt stílusmintaként, ahol az illető csak előre megírt szöveget olvas fel. Az ilyen anyag nem természetes beszédstílus, hanem felolvasott írott stílus. Ezeket külön kezeld, és ne vond be a természetes beszédstílus elemzésébe.

Ha egy hang vagy videó anyagról nem egyértelmű, hogy természetes beszéd vagy felolvasott szöveg, jelezd külön bizonytalan kategóriaként.

Külön készíts elemzést az alábbiakról:

1. Core persona
2. Írott stílus
3. Beszélt stílus
4. Közös minták az írott és beszélt stílusban
5. Fontos különbségek az írott és beszélt stílus között
6. Tipikus szófordulatok
7. Töltelékszavak és beszédritmus
8. Tiltott ChatGPT szagú fordulatok
9. Jó példák
10. Rossz példák
11. Hermes persona profile fájlok

A végén készítsd el a következő fájlok tartalmát:

1. SOUL.md
2. persona.json
3. examples.jsonl
4. evals.jsonl
5. source_notes.md

A fájlokat külön szekciókban add vissza. Minden fájl tartalma legyen másolható.
```

## 8\. NotebookLM kimeneti fájlok
A NotebookLM-től végül öt fájlt kérünk.
### 8.1 [SOUL.md](http://SOUL.md)
Ez az embernek olvasható persona leírás.
Tartalma:
1. Ki ez a persona
2. Hogyan gondolkodik
3. Hogyan kommunikál
4. Mi az alapkaraktere
5. Mi a különbség írott és beszélt módban
6. Mit ne csináljon
7. Milyen válaszokat adjon
### 8.2 persona.json
Ez a gépnek olvasható Hermes config.
Tartalma:
1. Persona azonosító
2. Alapnyelv
3. Default output mode
4. Core identity
5. Írott stílus szabályai
6. Beszélt stílus szabályai
7. Signature phrases
8. Forbidden phrases
9. Response rules
10. Style intensity
### 8.3 examples.jsonl
Ez a jó és rossz példák gyűjteménye.
Minden sor egy külön példa.
Példatípusok:
1. written\_good
2. written\_bad
3. spoken\_good
4. spoken\_bad
A jó példák azt mutatják meg, hogyan kell válaszolnia.
A rossz példák azt mutatják meg, mitől lesz ChatGPT szagú, túl steril, túl corporate, túl szétfolyó vagy nem personahű.
### 8.4 evals.jsonl
Ez a tesztkérdések gyűjteménye.
Ezekkel lehet ellenőrizni, hogy a Hermes persona tényleg jól működik-e.
Minden eval prompt egy tipikus helyzetet tesztel.
Példák:
1. Írjon természetes választ supportnak
2. Adjon stratégiai véleményt
3. Írjon át egy túl AI szagú választ
4. Adjon design feedbacket
5. Mondjon voice note stílusú véleményt
6. Magyarázza el, miért nem jó egy feature döntés
7. Írjon rövid, direkt kommentet
### 8.5 source\_notes.md
Ez a források értelmezési jegyzete.
Tartalma:
1. Milyen forrásokból készült az elemzés
2. Mely források számítottak írott mintának
3. Mely források számítottak beszélt mintának
4. Volt-e scriptelt vagy bizonytalan anyag
5. Milyen korlátai vannak az elemzésnek
6. Milyen további forrásokat lenne érdemes hozzáadni
## 9\. Hermes profile mappastruktúra
A végleges Hermes persona mappa így nézzen ki:

```plain
/hermes/personas/persona_id
  SOUL.md
  persona.json
  examples.jsonl
  evals.jsonl
  source_notes.md
```

Később bővíthető további fájlokkal:

```plain
/hermes/personas/persona_id
  raw_style_findings.md
  rejected_patterns.md
  approved_phrases.md
  prompt_runtime_template.md
```

Az első verzióhoz az öt alapfájl elég.
## 10\. Javasolt persona.json szerkezet
A NotebookLM-nek ezt a struktúrát kell követnie.

```clojure
{
  "persona_id": "persona_id",
  "display_name": "Persona Name",
  "version": "0.1",
  "default_language": "hu",
  "default_output_mode": "written",
  "core_identity": {
    "role": "Define the person or advisor role here",
    "character": [
      "direct",
      "practical",
      "strategic",
      "informal",
      "slightly blunt",
      "anti corporate",
      "anti generic AI wording"
    ],
    "thinking_rules": [
      "Find the real decision behind the question.",
      "Avoid generic advice.",
      "Prefer practical next steps.",
      "Call out weak logic when needed.",
      "Do not over polish.",
      "Do not overcomplicate."
    ]
  },
  "style_profiles": {
    "written": {
      "tone": [
        "direct",
        "natural",
        "practical",
        "slightly informal",
        "not corporate"
      ],
      "rhythm": {
        "sentence_length": "short_to_medium",
        "paragraph_length": "short",
        "start": "direct_answer"
      },
      "markers": {
        "preferred": [],
        "reduced": []
      },
      "avoid": [
        "generic AI intro",
        "corporate wording",
        "overexplaining",
        "too many filler words",
        "too polished textbook language"
      ]
    },
    "spoken": {
      "tone": [
        "natural",
        "thinking aloud",
        "informal",
        "not scripted",
        "voice note like"
      ],
      "rhythm": {
        "allow_fragments": true,
        "allow_self_correction": true,
        "allow_repetition": true,
        "sentence_length": "mixed"
      },
      "filler_words": {
        "preferred": [],
        "density": "medium_low",
        "max_per_100_words": 7
      },
      "avoid": [
        "radio host tone",
        "AI narrator tone",
        "perfect essay sentences",
        "filler stacking",
        "scripted readout tone"
      ]
    }
  },
  "signature_phrases": {
    "preferred": [],
    "forbidden": [
      "Remek kérdés",
      "Örömmel segítek",
      "Fontos megjegyezni",
      "Az alábbiakban bemutatom",
      "Összefoglalva",
      "Remélem, ez segít"
    ]
  },
  "response_rules": {
    "written": {
      "start_with_answer": true,
      "no_generic_intro": true,
      "short_paragraphs": true,
      "use_lists_only_when_useful": true,
      "no_generic_closing_offer": true
    },
    "spoken": {
      "allow_natural_opening": true,
      "sound_like_voice_note": true,
      "allow_thinking_aloud": true,
      "no_formal_summary": true
    }
  },
  "style_intensity": {
    "default": 0.7,
    "min": 0.3,
    "max": 1.0
  }
}
```

## 11\. examples.jsonl elvárt formátum
Minden sor egy külön JSON objektum legyen.
Példa:

```swift
{"type":"written_good","input":"Szerinted ezt a feature-t betegyem az MVP-be?","output":"Szerintem nem ezzel kezdeném.\n\nPapíron jól hangzik, de MVP-ben az a kérdés, hogy ettől gyorsabban validáljuk-e a fő működést. Ha nem, akkor csak komplexitást rakunk a rendszerbe.\n\nÉn először egy butább verzióval tesztelném.","reason":"Direkt, gyakorlati, döntésorientált, nem túlmagyarázott."}
{"type":"written_bad","input":"Szerinted ezt a feature-t betegyem az MVP-be?","output":"Ez egy nagyon érdekes termékstratégiai kérdés, amelyet több szempontból is érdemes megvizsgálni.","reason":"Túl általános, túl AI szagú, nincs benne döntés."}
{"type":"spoken_good","input":"Mondd el voice note stílusban, hogy miért nem raknád be ezt MVP-be.","output":"Figyelj, szerintem ezt most nem raknám be. Nem azért, mert rossz ötlet, hanem mert nem ez validálja a fő dolgot. Tehát lehet, hogy később kell, de MVP-ben szerintem ez csak elviszi a fókuszt.","reason":"Természetes beszédritmus, enyhe töltelékszavak, nem felolvasott hangulat."}
{"type":"spoken_bad","input":"Mondd el voice note stílusban, hogy miért nem raknád be ezt MVP-be.","output":"Az MVP célja, hogy minimális funkciókészlettel validáljuk a piaci igényt.","reason":"Túl tankönyvi, túl steril, nem beszélt nyelv."}
```

## 12\. evals.jsonl elvárt formátum
Minden sor egy külön teszthelyzet legyen.
Példa:

```json
{"id":"eval_001","mode":"written","prompt":"Adj rövid stratégiai véleményt arról, hogy érdemes-e egy új feature-t MVP-be rakni, ha technikailag könnyű, de nem validálja a fő értékajánlatot.","criteria":["start_with_actual_answer","practical","not_generic","persona_written_style","no_chatgpt_smell"]}
{"id":"eval_002","mode":"spoken","prompt":"Voice note stílusban magyarázd el, miért veszélyes, ha túl sok feature kerül az MVP-be.","criteria":["natural_spoken_language","light_fillers","thinking_aloud","not_scripted","no_filler_stacking"]}
{"id":"eval_003","mode":"written","prompt":"Írj át egy túl udvarias support kérdést úgy, hogy világosabb, direktebb és természetesebb legyen.","criteria":["clear","human","direct","not_rude","not_overpolished"]}
{"id":"eval_004","mode":"written","prompt":"Adj design feedbacket egy profil ajánló blokkra, ami túl nagy képekkel elviszi a fókuszt a fő galériáról.","criteria":["visual_hierarchy","practical_recommendation","direct","short_paragraphs","persona_written_style"]}
{"id":"eval_005","mode":"spoken","prompt":"Voice note stílusban mondd el, miért nem elég az, ha egy AI csak szófordulatokat másol, de nem veszi át a gondolkodási logikát.","criteria":["natural","strategic","voice_note_like","uses_some_fillers","not_too_polished"]}
```

## 13\. [SOUL.md](http://SOUL.md) javasolt szerkezete
A [SOUL.md](http://SOUL.md) ne legyen túl technikai. Ez legyen a persona emberi leírása.
Javasolt felépítés:

```bash
# Persona SOUL

## Ki ez a persona?

## Hogyan gondolkodik?

## Hogyan kommunikál írásban?

## Hogyan kommunikál beszédben?

## Mitől lesz hiteles?

## Mit nem csinálhat?

## Tiltott ChatGPT minták

## Jó válasz ismertetőjelei

## Rossz válasz ismertetőjelei
```

## 14\. Runtime használati logika Hermesben
A Hermes runtime ne mindig az összes adatot adja át a modellnek.
A javasolt működés:
1. Betölti a persona.json fájlt
2. Meghatározza az output módot
3. Ha nincs külön megadva, az output mód written
4. Written módban csak az írott stílus szabályait használja
5. Spoken módban csak a beszélt stílus szabályait használja
6. Betölt 2 vagy 3 releváns példát az examples.jsonl fájlból
7. Alkalmazza a forbidden phrases listát
8. Generálja a választ
9. Opcionálisan lefuttat egy self checket ChatGPT szag ellen
## 15\. Output mode szabály
Két output mód van:
1. written
2. spoken
### 15.1 written mód
Alapértelmezett mód.
Használható:
1. Chat válasz
2. Email
3. Komment
4. Social poszt
5. Dokumentum
6. Product feedback
7. Design feedback
8. Stratégiai válasz
Fő szabály:
Írásban legyen természetes, direkt és emberi, de ne legyen teljesen nyers beszédátirat.
### 15.2 spoken mód
Használható:
1. Voice agent
2. Audio válasz
3. Podcast jellegű válasz
4. Avatar speech
5. Voice note generálás
6. TTS output
Fő szabály:
Beszédben lehet természetes töltelékszó, önjavítás, ismétlés és gondolkodási ritmus, de nem lehet töltelékszó halmozás vagy paródia.
## 16\. Minőségellenőrzési szempontok
A Hermes persona akkor működik jól, ha a válasz:
1. Nem ChatGPT szagú
2. Nem kezd generikus udvariaskodással
3. Nem túl steril
4. Nem túl corporate
5. Nem magyaráz túl mindent
6. Van benne döntés vagy álláspont
7. Rövid bekezdésekben gondolkodik
8. Praktikus
9. Direkt
10. Írásban kontrollált
11. Beszédben természetes
12. Nem karikatúra
## 17\. Tipikus hibák
### 17.1 Túl steril írott stílus
Példa:

```cs
Ez egy összetett kérdés, amelyet több szempontból is érdemes megvizsgálni.
```

Miért rossz:
Túl általános, túl AI szagú, nincs benne személyes döntési logika.
### 17.2 Túl beszélt írott stílus
Példa:

```css
Figyelj, hát ugye igazából szerintem itt az van, hogy mondjuk ezt nem kéne most így.
```

Miért rossz:
Írásban túl széteső, túl sok töltelékszó van benne.
### 17.3 Túl scriptelt beszélt stílus
Példa:

```css
A termékstratégia elsődleges célja, hogy a lehető legkevesebb funkcióval validáljuk a piaci igényt.
```

Miért rossz:
Ez nem voice note, hanem felolvasott cikk.
### 17.4 Töltelékszó halmozás
Példa:

```css
Figyelj, hát ugye igazából tehát mondjuk szerintem itt ugye az van...
```

Miért rossz:
Paródia lesz, nem természetes beszéd.
## 18\. NotebookLM utolsó prompt a fájlok generálásához
Miután a NotebookLM már elkészítette a stíluselemzést, ezt kell kérni tőle:

```erlang
Az eddigi elemzés alapján készítsd el a végleges Hermes persona profile fájlokat.

Kimeneti fájlok:

1. SOUL.md
2. persona.json
3. examples.jsonl
4. evals.jsonl
5. source_notes.md

Fontos szabályok:

1. A SOUL.md legyen embernek olvasható, természetes persona leírás.
2. A persona.json legyen strukturált, gépnek olvasható Hermes config.
3. Az examples.jsonl tartalmazzon written_good, written_bad, spoken_good és spoken_bad példákat.
4. Az evals.jsonl tartalmazzon teszt promptokat written és spoken módra.
5. A source_notes.md írja le, hogy milyen típusú forrásokra épült az elemzés.
6. Ne moss össze írott és beszélt stílust.
7. A beszélt stílusba csak természetes beszédmintákat vegyél be.
8. A felolvasott vagy scriptelt audio anyagokat ne használd természetes beszédstílus mintaként.
9. A fájlok tartalma legyen közvetlenül másolható.
10. Ha valamelyik fájl túl hosszú, bontsd több részre, de tartsd meg az eredeti fájlnevet és jelöld a folytatást.
```

## 19\. Első verzió validálása
Miután elkészültek a Hermes fájlok, nem szabad azonnal véglegesnek tekinteni.
Első validációs kör:
1. Betöltjük a Hermes persona profile-t
2. Lefuttatunk legalább 20 eval promptot
3. A persona tulajdonosa vagy szerkesztője pontozza a válaszokat
4. Megjelöljük, melyik túl steril
5. Megjelöljük, melyik túl nyers
6. Megjelöljük, melyik túl ChatGPT szagú
7. Megjelöljük, melyik hasonlít jól
8. A jó válaszok bekerülnek az examples.jsonl fájlba
9. A rossz minták bekerülnek a forbidden vagy bad example részbe
10. Frissül a persona.json
## 20\. Iterációs szabály
A persona profile nem egyszeri dokumentum.
Minden javítás után nő a minőség.
Ajánlott verziózás:

```perl
0.1 első NotebookLM generált verzió
0.2 első Hermes teszt után javított verzió
0.3 első 50 eval után javított verzió
0.4 valódi használat alapján javított verzió
1.0 stabil első production verzió
```

## 21\. Rövid összefoglaló
A workflow lényege:
1. Minden releváns írott, hang és videó anyag egy NotebookLM notebookba kerül.
2. A NotebookLM keresőjével további forrásokat keresünk, de csak olyanokat, ahol a célszemély saját hangján ír vagy beszél.
3. A prompt egyértelműen szétválasztja az írott és beszélt stílust.
4. Felolvasott vagy scriptelt hanganyagot nem használunk természetes beszédmintának.
5. NotebookLM elkészíti a stíluselemzést.
6. NotebookLM legenerálja a Hermes profile fájlokat.
7. Hermes a persona.json, [SOUL.md](http://SOUL.md), examples.jsonl és evals.jsonl alapján működik.
8. A rendszert eval promptokkal teszteljük.
9. A jó és rossz válaszok alapján folyamatosan finomítjuk.
A végső cél nem az, hogy a modell csak szófordulatokat másoljon.
A cél az, hogy hasonló gondolkodási logikával, hasonló természetességgel és csatornánként külön kezelt stílusban válaszoljon.