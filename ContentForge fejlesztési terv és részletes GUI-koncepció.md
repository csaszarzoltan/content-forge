# ContentForge fejlesztési terv és részletes GUI-koncepció

**Verzió:** 1.0  
**Dátum:** 2026. augusztus 5.  
**Alap:** a csatolt ContentForge projekt kódja és dokumentációja, valamint 2026. augusztus 5-ig elérhető nyilvános versenytársi és szakmai források.

## 1. Vezetői összefoglaló

A ContentForge erős technikai alapokkal rendelkező, AI-támogatott content operations platform. A projekt már lefedi a márkahang-profilokat, tartalomgenerálást, validációt, SEO-t, fordítást, időzítést, publikálást, analitikát, A/B tesztelést és több munkaterületet. A legnagyobb hiány nem egy újabb önálló AI-funkció, hanem az, hogy ezek nem mindenhol alkotnak egységes, tartós, biztonságos és könnyen használható kampányfolyamatot.

A javasolt termékirány:

> **ContentForge legyen többmárkás és többnyelvű csapatok irányított AI content operations rendszere, amely a briefből ellenőrzött, jóváhagyott, publikált és mérhető tartalmat készít.**

A piac azt mutatja, hogy a felhasználók egyetlen rendszerben szeretnék kezelni a tervezést, készítést, visszajelzést, jóváhagyást, publikálást és mérést. A szétszórt e-mailek, chatüzenetek, táblázatok és dokumentumok helyett világos felelősséget, verziókövetést és látható következő lépést várnak. A content operations kategóriában az approval workflow, a valós idejű együttműködés, a verziókezelés, a lokalizáció, a governance és a publikálási megbízhatóság vált alapelvárássá ([EasyContent](https://easycontent.io/resources/best-content-operations-platforms/), [Planable](https://planable.io/), [Sprout Social](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows)).

A terv öt egymásra épülő programot javasol:

1. **Biztonsági és adatplatform-alapok**
2. **Egységes kampány-cockpit és tartalomszerkesztő**
3. **Validációs és jóváhagyási rendszer**
4. **Megbízható időzítés, publikálás és helyreállítás**
5. **Lokalizációs és teljesítmény-visszacsatolási hurok**

A fejlesztés 24 hetes, öt inkrementumból álló roadmapként tervezhető. Az első 12 hét célja egy működő, biztonságos create-to-publish „vertical slice”, nem pedig további szélességi funkciók hozzáadása.

---

## 2. Kutatási módszertan és bizonyítékok

### 2.1 A projektből megállapított helyzet

A csatolt projekt alapján a ContentForge:

- FastAPI és aszinkron SQLAlchemy alapú backenddel rendelkezik;
- márkahang-, generálási, scheduling-, publishing-, analytics- és A/B teszt modelleket tartalmaz;
- platformvalidációt biztosít X, LinkedIn, Instagram, Facebook és TikTok irányban;
- publikálási konnektorarchitektúrát tartalmaz, de a tényleges publishing főként X és LinkedIn esetén teljes;
- többnyelvű generálást, nyelvdetektálást, fordítást és minőségmérést tartalmaz;
- hat fő munkaterületet definiál: Campaign, Asset, Approval, Publish, Localization, Provenance;
- a UI több ponton inkább demonstrációs vagy olvasási felület, mint teljes műveleti rendszer;
- egyes publishing- és scheduling-állapotokat memóriában vagy részlegesen kezel;
- nem minden kritikus workflow rendelkezik tartós állapottal, idempotenciával, diffel, teljes recoveryvel vagy valós platform-visszaellenőrzéssel.

### 2.2 Külső kutatási minta

A terv az alábbi termékkategóriákat vizsgálta:

- social content collaboration és approval: Planable, Sprout Social;
- content operations és workflow: Contentful, Wrike, CoSchedule, EasyContent;
- AI brand governance: WRITER, Frontify, Contentoo, Brande.ai;
- lokalizációs workflow: Lokalise, Contentful Localization;
- általános piaci összehasonlítások és felhasználói igények: The CMO, EasyContent és szakmai workflow-összefoglalók.

A kutatás korlátja, hogy nyilvános marketingoldalak és dokumentációk nem helyettesítik a ContentForge saját célfelhasználóival végzett interjúkat. Ezért a roadmap első szakaszában külön discovery és usability validáció szükséges.

---

## 3. Felhasználói igények és Jobs-to-be-Done

### 3.1 Elsődleges felhasználók

#### Content marketing manager

Feladata a kampány briefje, határideje, célcsatornái, jóváhagyási folyamata és eredménye. A legfontosabb szükséglete, hogy mindig lássa:

- hol tart a kampány;
- mi akadályozza;
- kihez tartozik a következő lépés;
- melyik tartalom publikálható biztonságosan;
- mi teljesített jól.

#### Content creator vagy copywriter

Gyorsan szeretne márkahű első verziót előállítani, biztonságosan szerkeszteni, autosave-vel dolgozni, a hibákat konkrét helyen látni, majd review-ra küldeni.

#### Reviewer, brand vagy legal approver

Nem akar teljes kampányokat átböngészni. Csak a rá váró elemeket, a változásokat, a validációs kockázatokat és a korábbi megjegyzésekre adott válaszokat akarja látni.

#### Social media manager vagy publisher

Biztos akar lenni abban, hogy a jóváhagyott változat, a megfelelő fiókra, helyes időzónában, duplikáció nélkül kerül ki. Sikertelenség esetén csatornánkénti újrapróbálást és egyértelmű recoveryt vár.

#### Localization manager és translator

Forrás és célnyelvi változatokat akar egymás mellett kezelni, terminológiával, fordítási memóriával, nyelvenkénti review-státusszal és kontextussal. A lokalizáció repeatable workflow, nem egyszeri fordítási művelet ([SimpleLocalize](https://simplelocalize.io/blog/posts/what-is-a-localization-workflow/), [Lokalise](https://lokalise.com/product/localization-workflow-management/)).

#### Agency account lead

Több ügyfél munkáját kezeli. Ügyfélizolációt, gyors váltást, külső review-linket, white-label riportot és bizonyítható jóváhagyást igényel.

### 3.2 Fő felhasználói fájdalmak

1. A tartalom, feedback és jóváhagyás több rendszer között szétszóródik.
2. Nem világos, melyik verzió a publikálható változat.
3. A feedback nem a konkrét szövegrészhez kapcsolódik.
4. A publikálási hiba után nem egyértelmű, hogy újra lehet-e próbálni duplikáció nélkül.
5. Az AI gyorsítja az első draftot, de növeli a brand drift és compliance kockázatát.
6. A fordítás sokszor elveszíti a márkahangot és a lokális kontextust.
7. Nagy mennyiségnél hiányzik a személyes feladatlista, keresés és tömeges művelet.

A versenytársi gyakorlat is ezeket a problémákat célozza. A Planable a tartalom mellett elhelyezett feedbacket, natív platformelőnézetet és többszintű approvalt hangsúlyoz; a Sprout Social egyszerű, többfelhasználós és többlépcsős approval workflow-kat kínál; a Contentful a lokalizációt szerepkörökkel és nyelvenkénti review-lépésekkel kapcsolja össze ([Planable](https://planable.io/), [Sprout Social](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows), [Contentful](https://www.contentful.com/products/platform/localization-and-translation/)).

---

## 4. Versenytársi tanulságok

### 4.1 Planable

**Erősségek:** natív platformhoz hasonló előnézetek, kontextusban elhelyezett kommentek, suggestion és annotation, több tartalomnézet, kliensbarát approval. Négy approval modell közül lehet választani: nincs, opcionális, kötelező és többszintű ([Planable product](https://planable.io/), [Planable approval dokumentáció](https://help.planable.io/hc/en-us/articles/21715462785180-Approvals-and-Approval-Workflows)).

**ContentForge-tanulság:** az approval ne külön adminoldal legyen, hanem a tartalom mellett működjön. A reviewernek a platformelőnézetből kell tudnia kommentelni és jóváhagyni.

### 4.2 Sprout Social

**Erősségek:** jogosultságvezérelt publikálás, több lépés, lépésenként több reviewer, „Any” vagy „All” jóváhagyási szabály. A cél a hibás vagy off-brand posztok megelőzése és az agency-client review támogatása ([Sprout approval workflow](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows), [Sprout approval process](https://sproutsocial.com/insights/social-media-approval/)).

**ContentForge-tanulság:** a workflow sablonok legyenek kockázatalapúak. Egy alacsony kockázatú organikus poszt és egy szabályozott termékállítás ne ugyanazt a jóváhagyási utat járja be.

### 4.3 Contentful

**Erősségek:** strukturált tartalom, locale-alapú publishing, automatizált lokalizációs trigger, szerepkörös review, egy workflow-n belüli nyelvenkénti handoff ([Contentful localization](https://www.contentful.com/products/platform/localization-and-translation/), [Localized workflows](https://www.contentful.com/help/ai-automations/workflows/localized-workflows/)).

**ContentForge-tanulság:** a fordítás ne másolat legyen. A locale legyen elsőrangú állapotdimenzió, saját ownerrel, státusszal, terminológiával és publish readiness jelzéssel.

### 4.4 Lokalise

**Erősségek:** automatikus task-létrehozás, workflow sablonok, translation memory, bulk műveletek, szűrés, webhookok, progress dashboard és fejlesztői integrációk ([Lokalise workflows](https://lokalise.com/product/localization-workflow-management/), [Lokalise workflow dokumentáció](https://docs.lokalise.com/en/articles/9582608-workflows)).

**ContentForge-tanulság:** a lokalizációs workspace-nek feladat- és kivételközpontúnak kell lennie. A felhasználó azt akarja látni, mely nyelvek készek, hol van QA-hiba, és mi blokkolja a publikálást.

### 4.5 WRITER, Frontify és AI brand governance

A modern brand governance nem statikus PDF, hanem a generálás pillanatában érvényesített standardok, jó példák, terminológia, csatornaszabályok és szervezeti override-ok rendszere. A WRITER 2026-os brand tooling iránya a style guide és terminológia közvetlen végrehajtásba építését hangsúlyozza; a Frontify szintén az approved assets és brand rules központi, workflow-ba kötött forrásaként pozicionálja a governance-et ([WRITER bejelentés](https://www.businesswire.com/news/home/20260528415571/en/WRITER-Solves-AIs-Brand-Governance-Crisis-with-New-Infrastructure-for-Enterprise-Marketing-at-Scale), [Frontify guide](https://www.frontify.com/en/guide/ai-for-brand-management), [Contentoo](https://www.contentoo.com/blog/brand-voice-governance-ai-content)).

**ContentForge-tanulság:** a brand score önmagában kevés. A rendszernek mondatszintű magyarázatot, jó példát, quick fixet, szabályverziót és override indoklást kell adnia.

---

## 5. Céltermék és információs architektúra

### 5.1 Fő navigáció

A jelenlegi hat workspace megőrizhető, de egy egységes shell és kampánykontextus szükséges.

**Bal oldali főmenü:**

1. My Work
2. Campaigns
3. Content
4. Calendar
5. Approvals
6. Localization
7. Analytics
8. Brand Governance
9. Connections
10. Admin

**Felső globális sáv:**

- workspace vagy ügyfélváltó;
- globális keresés;
- gyors létrehozás;
- értesítések;
- help és parancspaletta;
- felhasználói menü.

**Kontextussáv kampányon belül:**

- kampánynév;
- státusz;
- owner;
- határidő;
- célcsatornák;
- nyelvek;
- readiness score;
- következő blokkoló lépés.

### 5.2 Közös státuszmodell

A kampány- és asset-státuszok legyenek explicit állapotgépek:

- Draft
- In generation
- In editing
- Validation required
- Needs changes
- Waiting for approval
- Approved
- Scheduled
- Publishing
- Partially published
- Published
- Failed
- Archived

Minden változás atomikus eseményt és auditbejegyzést hozzon létre. A UI ne csak színnel, hanem ikonnal és szöveggel is jelezze az állapotot.

---

## 6. Részletes GUI-tervek

# 6.1 My Work dashboard

## Cél

A felhasználó 30 másodpercen belül megértse, mi igényel figyelmet, és egy kattintással folytathassa a munkát.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Workspace: Acme Europe ▼   Search…         + Create      Alerts  Avatar │
├──────────────┬───────────────────────────────────────────────────────────┤
│ My Work      │ Good morning, Anna                               [Today] │
│ Campaigns    │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│ Content      │ │ 8 review │ │ 3 failed │ │ 12 today │ │ 2 blockers   │ │
│ Calendar     │ └──────────┘ └──────────┘ └──────────┘ └──────────────┘ │
│ Approvals    │                                                           │
│ Localization │ My queue                         Filter ▼  Sort ▼          │
│ Analytics    │ ┌───────────────────────────────────────────────────────┐ │
│ Brand        │ │ High | Legal approval | Launch email | Due 14:00    │ │
│ Connections  │ │ [Open review]                                         │ │
│ Admin        │ ├───────────────────────────────────────────────────────┤ │
│              │ │ Failed | LinkedIn publish | Retry available          │ │
│              │ │ [Inspect failure] [Retry failed channel]             │ │
│              │ └───────────────────────────────────────────────────────┘ │
│              │                                                           │
│              │ Continue working                                          │
│              │ [Campaign card] [Draft card] [Localization card]          │
└──────────────┴───────────────────────────────────────────────────────────┘
```

## Interakciók

- A prioritás az SLA, publish időpont, blokkoló státusz és felhasználói szerep alapján számolódik.
- A kártyák mindig konkrét elsődleges műveletet mutatnak.
- A „Snooze”, „Assign”, „Open in new tab” műveletek overflow menüben jelennek meg.
- Mentett szűrők: „My approvals”, „Publishing failures”, „Due today”, „Client X”.

## Állapotok

- **Üres:** „Nincs rád váró feladat. Folytasd egy kampányból vagy hozz létre újat.”
- **Betöltés:** skeleton kártyák.
- **Részleges hiba:** a működő widgetek megmaradnak, a hibás panel külön retryt kap.
- **Offline:** utolsó frissítés időpontja, refresh gomb.

## Mobil

A bal menü drawer lesz. A kártyák egy oszlopban jelennek meg. A négy KPI vízszintesen görgethető, de a feladatlista nem rejtett carousel kezdőállapotban.

---

# 6.2 Campaign Cockpit

## Cél

Egyetlen képernyőn egyesíteni a briefet, asseteket, állapotot, approvalt, lokalizációt, publishingot és eredményeket.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Campaigns / Summer Launch          Approved  82% ready   [Publish ▼]  │
│ Owner Anna | Due Aug 14 | 5 channels | 4 locales | Last saved now       │
├──────────────────────────────────────────────────────────────────────────┤
│ Overview | Content 12 | Approvals 3 | Localization | Publish | Analytics│
├───────────────────────┬────────────────────────────┬─────────────────────┤
│ Brief                 │ Asset pipeline             │ Activity / blockers │
│ Goal                  │ Draft  Review Approved     │ 2 legal warnings    │
│ Audience              │ [card] [card] [card]       │ DE translation late │
│ Offer                 │                            │ LinkedIn token exp.  │
│ Brand profile         │ + Generate content         │ [Resolve blockers]   │
│ [Edit brief]          │                            │                     │
├───────────────────────┴────────────────────────────┴─────────────────────┤
│ Next recommended action: Resolve legal claim in “Launch email v3”       │
│ [Open asset]                                                        │
└──────────────────────────────────────────────────────────────────────────┘
```

## Fő komponensek

- readiness score összetevőkkel;
- blocker panel;
- asset pipeline státuszoszlopokkal;
- kampánybrief összefoglaló;
- locale és platform coverage;
- eseményfolyam;
- egyértelmű „Next recommended action”.

## Üzleti szabályok

- Publish csak akkor aktív, ha nincs blokkoló validáció és a szükséges approvalok megvannak.
- A readiness score kattintható és megmagyarázza a hiányzó feltételeket.
- A kampány állapota a kapcsolt assetekből és publish műveletekből determinisztikusan származik.

---

# 6.3 Content Editor és verziókezelés

## Cél

Biztonságos, gyors szerkesztés valós idejű platform-, SEO-, brand- és compliance-visszajelzéssel.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Launch LinkedIn post   v7 ▼   Saved now   Owner Anna   [Request review]│
├───────────────┬────────────────────────────────┬─────────────────────────┤
│ Outline       │ Editor                         │ Quality panel           │
│ Hook          │ [Rich text / structured fields]│ Brand voice 86         │
│ Value         │                                │ SEO 74                 │
│ Proof         │ Selected text...               │ Platform 100           │
│ CTA           │                                │ Compliance 62          │
│               │                                │                         │
│ Sources       │                                │ Issues                  │
│ Brand refs    │                                │ [Blocker] claim lacks  │
│               │                                │ source                  │
│               │                                │ [Fix] [Explain]         │
├───────────────┴────────────────────────────────┴─────────────────────────┤
│ Preview: LinkedIn desktop | mobile | raw text    [Compare versions]     │
└──────────────────────────────────────────────────────────────────────────┘
```

## Kötelező funkcionalitás

- 2 másodpercen belüli autosave idle után;
- mentési státusz és retry;
- explicit verzió létrehozása review vagy publish előtt;
- diff nézet szó- és blokk-szinten;
- verzió visszaállítása új verzióként;
- komment és suggestion kijelölt szöveghez;
- platformelőnézet szerkesztés közben;
- validáció debounce-szal;
- quick fix előnézettel, soha nem automatikus felülírással;
- források és állítások kapcsolása;
- szerkesztési lock vagy optimista concurrency ETaggel.

## Billentyűzet és accessibility

- `Ctrl+S`: azonnali mentés;
- `Ctrl+Shift+Enter`: review kérése;
- `Alt+1..4`: minőségpanelek;
- minden issue fókuszálható és az érintett szövegre navigál;
- screen reader live region jelzi a mentést és validációt;
- diff nem csak színnel jelöl.

---

# 6.4 Approval workspace

## Cél

A reviewer minimális kontextusvesztéssel, biztonságosan tudjon dönteni.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Approvals   My queue 8       Campaign ▼ Risk ▼ Due ▼                    │
├──────────────────┬────────────────────────────────┬──────────────────────┤
│ Queue            │ Content + platform preview     │ Decision panel       │
│ [High] Email     │                                │ Required checks 4/5  │
│ [Med] LinkedIn   │ Inline comments and diff       │ Brand: pass          │
│ [High] DE page   │                                │ Legal: warning       │
│                  │                                │ Locale: pass         │
│                  │                                │                      │
│                  │                                │ Comment              │
│                  │                                │ [Request changes]    │
│                  │                                │ [Approve]            │
└──────────────────┴────────────────────────────────┴──────────────────────┘
```

## Approval-modellek

- nincs approval;
- opcionális;
- kötelező egy reviewer;
- soros többszintű;
- párhuzamos „Any” vagy „All”;
- feltételes, például legal csak szabályozott állításnál.

Ezek a Planable és Sprout gyakorlatával összhangban vannak, ahol a workflow a csapat kockázatához és felelősségi modelljéhez igazítható ([Planable](https://help.planable.io/hc/en-us/articles/21715462785180-Approvals-and-Approval-Workflows), [Sprout Social](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows)).

## Döntési szabályok

- Approve csak akkor aktív, ha minden kötelező ellenőrzés teljesült vagy dokumentált override van.
- Request changes esetén legalább egy komment vagy indoklás kötelező.
- A döntés a verzióhoz kötött. Tartalommódosítás automatikusan visszavonja a korábbi approvalt, ha a workflow policy ezt előírja.
- Külső reviewer egyszer használatos, időkorlátos linket kaphat, csak a szükséges assethez.

---

# 6.5 Publish Center

## Cél

A felhasználó publikálás előtt és után is biztosan értse, mi történt minden egyes csatornán.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Publish Center                          [Schedule selected] [Publish now]│
├──────────────────────────────────────────────────────────────────────────┤
│ Campaign: Summer Launch   Timezone: Europe/Zurich   6 selected          │
│                                                                          │
│ Channel      Account       Readiness   Schedule       Status   Action    │
│ LinkedIn     Acme Global   Ready       Aug 14 09:00   Draft    Preview   │
│ X            @acme         Warning     Aug 14 09:05   Draft    Fix       │
│ Instagram    Acme EU       Blocked     --             Draft    Connect   │
│                                                                          │
│ Duplicate protection: On   Approval snapshot: v7   Idempotency: created │
└──────────────────────────────────────────────────────────────────────────┘
```

## Publikálási folyamat

1. Preflight ellenőrzés.
2. Approval snapshot rögzítése.
3. Idempotency key létrehozása.
4. Csatornánkénti queue-be helyezés.
5. Provider request és external ID mentése.
6. Webhook vagy polling reconciliation.
7. Audit és analytics kapcsolat.

## Hiba és recovery

- **Részleges siker:** sikeres csatornák változatlanok, csak a hibásak próbálhatók újra.
- **Timeout:** „Unknown external state”, először reconcile, utána retry.
- **Auth hiba:** connection center mélylink.
- **Rate limit:** következő automatikus próbálkozás időpontja.
- **Invalid media:** közvetlen asset-fix művelet.
- **Cancel:** csak queued állapotban garantált; publishing állapotban best-effort.

---

# 6.6 Connections Center

## Cél

A platformfiókok, jogosultságok és lejáró tokenek kezelése technikai beavatkozás nélkül.

## Képernyő

```text
Connections
[+ Connect account]

LinkedIn | Acme Global | Healthy | expires in 24 days | Last check 2 min ago
Permissions: post, read analytics
[Test] [Reconnect] [Disconnect]

X | @acme | Action required | token expired
[Reconnect]
```

## Követelmények

- teljes OAuth flow PKCE-vel, ahol támogatott;
- token refresh;
- titkosított tárolás;
- least privilege scope;
- kapcsolat tesztelése;
- account ownership és tenant scope;
- auditálható reconnect és disconnect;
- lejárati és permission-drift értesítés.

---

# 6.7 Localization workspace

## Cél

A fordítási státusz, QA, terminológia és helyi adaptáció egy képernyőn kezelhető legyen.

## Desktop wireframe

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Localization | Summer Launch | Source: EN | 4 target locales            │
├──────────────┬───────────────────────────────┬───────────────────────────┤
│ Locales      │ Source / target editor        │ QA and terminology        │
│ DE  82%      │ EN             DE             │ 3 glossary mismatches     │
│ FR  Ready    │ side-by-side segments         │ 1 length overflow         │
│ ES  Review   │                               │ Brand voice 78            │
│ JA  Blocked  │ [Apply suggestion]             │ [Run QA] [Request review] │
├──────────────┴───────────────────────────────┴───────────────────────────┤
│ Translation memory match | Context screenshot | Comments | History      │
└──────────────────────────────────────────────────────────────────────────┘
```

## Funkciók

- forrás és célnyelv egymás mellett;
- segment status;
- translation memory;
- glossary és tiltott terminológia;
- locale-specifikus brand voice;
- human review queue;
- character limit és platform preview;
- bulk AI translation, de kötelező review policy konfigurálható;
- automation trigger új vagy módosított forrástartalomra;
- nyelvenkénti workflow és owner.

A Lokalise és Contentful mintája alapján a workflow-nak automatikusan feladatot kell létrehoznia új vagy módosított tartalomra, és a fordítást review-lépéshez kell kötnie ([Lokalise](https://docs.lokalise.com/en/articles/9582608-workflows), [Contentful](https://www.contentful.com/help/ai-automations/workflows/localized-workflows/)).

---

# 6.8 Brand Governance Center

## Cél

A márkahang ne statikus dokumentum, hanem verziózott, tesztelhető és érvényesíthető szabályrendszer legyen.

## Fő nézetek

1. Profiles
2. Terminology
3. Examples
4. Channel rules
5. Compliance policies
6. Test lab
7. Change history

## Voice Profile Editor

```text
Brand profile: Acme Core v12                   Draft [Publish profile]
Voice attributes       Terminology             Approved examples
Confident  80          Use: "customers"        Good / bad pairs
Warm       62          Avoid: "users"          Channel examples
Technical  45

[Test sample text] [Compare with v11] [Request governance approval]
```

## Kulcsfunkciók

- Do/Don't példák;
- csatorna-, régió- és közönségspecifikus override;
- glossary enforcement;
- profilverzió és approval;
- test corpus;
- score magyarázat;
- mondatszintű issue;
- szabályonként severity és override policy;
- rollback.

---

# 6.9 Analytics és learning loop

## Cél

Az analytics ne statikus riport legyen, hanem következő műveletet javasoljon.

## Fő nézet

- campaign outcome;
- channel breakdown;
- content variant comparison;
- brand/compliance score és teljesítmény korreláció;
- locale comparison;
- approval cycle time;
- publish failure rate;
- anomaly explanation;
- recommended experiment.

## Drill-through

Minden grafikonból elérhető legyen az érintett assetlista, verzió, csatorna és időszak. A felhasználó hozhasson létre A/B tesztet vagy új változatot közvetlenül az insightból.

---

## 7. Funkcionális fejlesztési backlog

### P0, termékbiztonsági alapok

1. Tenant- és workspace-modell.
2. Object-level authorization minden API-n.
3. Egységes Campaign, Asset, Revision, Approval, Publication és LocaleVariant relációs modell.
4. Alembic migrációk.
5. Idempotency és deduplikáció publishingnál.
6. Tartós job queue és outbox pattern.
7. Audit event store.
8. Titkosított credential lifecycle és token refresh.
9. Strukturált hibacontract, correlation ID.
10. E2E cross-tenant security tesztek.

### P0, teljes kampányfolyamat

1. Campaign cockpit.
2. Asset editor autosave-vel.
3. Revision és diff.
4. Valós idejű validáció.
5. Approval workflow.
6. Schedule és publish preflight.
7. Channel-level status és recovery.
8. Analytics linkage.

### P1, napi hatékonyság

1. My Work dashboard.
2. Globális keresés.
3. Mentett szűrők.
4. Bulk actions.
5. Notification center.
6. Assignment, due date, SLA.
7. External review links.
8. Reusable campaign playbooks.

### P1, governance és lokalizáció

1. Brand profile editor és verziózás.
2. Explainable compliance.
3. Locale-specific voice.
4. Translation memory és glossary.
5. Side-by-side localization editor.
6. Language-specific approval.
7. Continuous localization triggers.

### P2, csatorna- és médiabővítés

1. Instagram, Facebook és TikTok konnektorok.
2. Media library.
3. Kép, videó és carousel upload.
4. Crop, aspect ratio és thumbnail.
5. Alt text és rights metadata.
6. Native-like previews.

---

## 8. Célarchitektúra

### 8.1 Domain réteg

- Campaign
- ContentAsset
- AssetRevision
- ValidationRun és Finding
- ApprovalWorkflow, ApprovalStep és Decision
- LocalizationJob és LocaleVariant
- PublicationIntent, PublicationAttempt és ExternalPublication
- PlatformConnection
- AnalyticsEvent és Experiment
- AuditEvent

### 8.2 Application services

- CreateCampaign
- GenerateAsset
- SaveRevision
- ValidateRevision
- RequestApproval
- RecordDecision
- SchedulePublication
- PublishWithIdempotency
- ReconcileExternalStatus
- CreateLocalizationJobs
- RecordAnalytics

### 8.3 Infrastructure

- PostgreSQL;
- Alembic;
- Redis és worker queue;
- object storage médiához;
- outbox és webhook inbox;
- OpenTelemetry;
- provider adapterek;
- secret manager production környezetben.

### 8.4 Frontend

Javasolt irány: React vagy Next.js TypeScript kliens, query cache-sel és szerveroldali API-contract generálással. A jelenlegi server-rendered felület fokozatosan migrálható, a route-ok és backend contractok megőrzésével.

**UI-technológiai elvek:**

- design tokenek;
- hozzáférhető komponenskönyvtár;
- optimista UI csak visszavonható műveleteknél;
- autosave state machine;
- websocket vagy SSE progresshez;
- URL-ben tárolt filter és nézetállapot;
- permission-aware komponensek, de a security mindig szerveroldali.

---

## 9. Nem funkcionális követelmények

### Biztonság

- Minden erőforrás tenant-scoped.
- Minden mutáció authorizationt és auditot igényel.
- OAuth token titkosított, logban soha nem jelenhet meg.
- External review link rövid életű, scope-olt és visszavonható.
- LLM input/output adatkezelési policy profilhoz kötött.
- Prompt injection és unsafe tool action ellen explicit trust boundary szükséges.

### Megbízhatóság

- Publikálás exactly-once hatású üzleti szemantikával, idempotens adapterrel.
- Webhook többszöri beérkezése deduplikálva.
- Minden hosszú művelet folytatható vagy determinisztikusan újraindítható.
- Részleges siker elsőrangú állapot.

### Teljesítmény

- Listaoldalak p95 válaszideje 500 ms alatt 10 000 tenant-elemnél.
- Editor autosave acknowledgement 1 másodpercen belül normál hálózaton.
- Validáció első részleges eredménye 2 másodpercen belül.
- Nagy listák szerveroldali lapozással és virtualizálással.

### Accessibility

- WCAG 2.2 AA.
- Teljes billentyűzetes használat.
- Látható fókusz.
- Logikus heading és landmark struktúra.
- Nem csak színalapú állapot.
- Accessible modal, drawer és toast.
- Screen reader számára érthető progress és autosave.

### Privacy és compliance

- adatmegőrzési policy;
- right-to-delete workflow;
- audit export;
- PII redaction;
- model provider adatküldési beállítás;
- régiós adattárolás enterprise csomagban.

---

## 10. Roadmap és inkrementumok

# Inkrementum 0: Discovery és foundation, 0–4. hét

**Cél:** bizonyított felhasználói problémák és biztonságos adatmodell.

- 8–12 interjú: marketing manager, creator, reviewer, publisher, localization, agency lead.
- 5 megfigyelt create-to-publish feladat.
- jelenlegi API/data audit;
- tenant és authorization threat model;
- cél domainmodell;
- Alembic és migration CI;
- audit/correlation alap;
- design system és navigációs shell prototípus.

**Kilépési feltétel:** cross-tenant tesztek zöldek, első kampány vertical slice adatmodellje migrálható, a Campaign Cockpit prototípus 5 felhasználóból legalább 4-nél feladatsegítség nélkül értelmezhető.

# Inkrementum 1: Campaign cockpit és editor, 5–9. hét

- kampány létrehozás és brief;
- cockpit;
- asset CRUD;
- editor autosave;
- revision és diff;
- platformpreview első két csatornára;
- alap live validation;
- My Work minimális queue.

**Kilépési feltétel:** briefből szerkeszthető, verziózott asset hozható létre API közvetlen használata nélkül.

# Inkrementum 2: Approval és governance, 10–13. hét

- approval workflow sablonok;
- inline comment, suggestion;
- required és multi-step approval;
- decision audit;
- brand profile editor;
- explainable findings;
- external reviewer link.

**Kilépési feltétel:** jóváhagyatlan vagy approval után módosított asset nem publikálható a policy megkerülésével.

# Inkrementum 3: Publishing confidence, 14–18. hét

- persistent publish history;
- job queue és outbox;
- idempotency;
- X és LinkedIn production hardening;
- connection center és token refresh;
- partial success;
- reconcile és selective retry;
- publish calendar.

**Kilépési feltétel:** timeout és ismételt request nem okoz duplikált publikációt, az újraindítás nem veszíti el a státuszt.

# Inkrementum 4: Localization és learning loop, 19–24. hét

- side-by-side localization editor;
- translation memory és glossary;
- locale workflow;
- language approval;
- analytics drill-through;
- A/B teszt létrehozása insightból;
- notification center;
- bulk actions.

**Kilépési feltétel:** egy jóváhagyott forrásassetből legalább három locale változat készíthető, review-zható és publikálható teljes audit traillel.

---

## 11. TDD és tesztstratégia

### Unit

- állapotátmenetek;
- readiness score;
- approval policy;
- idempotency;
- nested locale workflow;
- brand finding magyarázat;
- permission rules.

### Integráció

- adatbázis tranzakció és migration;
- outbox és worker;
- provider adapter fake szerverrel;
- webhook deduplikáció;
- token refresh;
- analytics attribution.

### Contract

- OpenAPI snapshot;
- versioned provider adapter contract;
- structured error payload;
- webhook schema.

### UI komponens

- autosave állapotok;
- diff;
- issue-to-editor navigation;
- permission-aware action;
- approval decision;
- partial publish recovery;
- locale comparison.

### E2E

1. kampány létrehozása → generálás → szerkesztés → validáció → approval → schedule → publish;
2. reviewer changes requested → creator javít → új approval;
3. kétcsatornás publish, egyik sikerül, másik rate limited → selective retry;
4. locale generálás → glossary hiba → javítás → locale approval;
5. cross-tenant hozzáférés blokkolása;
6. dupla publish request, egyetlen külső hatás.

### Accessibility

- axe alapú automatizált ellenőrzés;
- keyboard-only E2E;
- screen reader manuális smoke test;
- 200% zoom;
- high contrast.

---

## 12. Termékcsomagolás

### Community vagy Starter

- egy workspace;
- alap generálás és brand profile;
- manuális validation;
- egyszerű calendar;
- két platform kapcsolat;
- korlátozott analytics.

### Professional

- több workspace;
- approval workflow;
- revision/diff;
- localization;
- persistent publishing és recovery;
- advanced analytics;
- reusable playbooks;
- API és integrációk.

### Enterprise

- SSO/OIDC vagy SAML;
- SCIM;
- central policy;
- audit export;
- régiós deployment;
- custom retention;
- multi-level approval;
- legal/compliance rule packs;
- SLA és managed onboarding.

A Planable is az approval mélységével és workspace-kapacitással differenciálja a csomagokat, az enterprise szinthez többszintű approvalt társít ([Planable pricing](https://planable.io/pricing/)). A ContentForge esetén azonban az alap biztonsági és idempotenciafunkciók nem lehetnek fizetős extrák, mert azok a termék helyes működéséhez szükségesek.

---

## 13. Mérőszámok

### North star

**Havonta biztonságosan publikált, visszakövethető, jóváhagyott content assetek száma aktív workspace-enként.**

### Aktiváció

- első kampány létrehozásáig eltelt idő;
- első jóváhagyott asset;
- első sikeres publish;
- brand profile beállítási arány.

### Workflow

- median brief-to-publish idő;
- approval cycle time;
- validation issue resolution rate;
- recovery success rate;
- API nélkül teljesített flow aránya;
- My Work queue-ból indított műveletek aránya.

### Minőség

- publish success rate;
- duplicate publish incidens;
- rollback és restore siker;
- brand override arány;
- locale QA failure;
- cross-tenant authorization tesztek pass rate.

### Üzlet

- aktív workspace-ek;
- heti aktív creator/reviewer/publisher;
- Professional conversion;
- account expansion;
- churn oka;
- support ticket per 100 publish.

---

## 14. Kutatási és validációs terv

### Interjúk

- 4 in-house marketing csapat;
- 4 ügynökség;
- 2 lokalizációs szakember;
- 2 szabályozott iparági reviewer.

### Feladat-alapú usability teszt

1. kampány folytatása a My Work képernyőről;
2. korrigálandó brand issue megtalálása;
3. változtatás összehasonlítása és approval;
4. részlegesen hibás publish helyreállítása;
5. német locale review-ja.

### Sikerkritérium

- 85% vagy jobb task completion;
- kritikus műveletnél 0 súlyos félreértés;
- publish eredményét 5 másodpercen belül helyesen értelmező felhasználók aránya legalább 90%;
- SUS legalább 80 a második iteráció után;
- billentyűzetes kritikus flow 100%-ban teljesíthető.

---

## 15. Fő kockázatok és mitigáció

### Túl széles scope

**Mitigáció:** vertical slice, új konnektorok tiltása a publish hardening befejezéséig.

### AI false positive és governance fatigue

**Mitigáció:** explainable finding, severity, override, feedback loop és szabályonkénti minőségmérés.

### Külső platform bizonytalan állapota

**Mitigáció:** idempotency, external ID, webhook inbox, reconciliation és manual verification.

### Lokalizációs minőség túlzott automatizálása

**Mitigáció:** kockázatalapú human review, glossary, translation memory és locale owner.

### Enterprise complexity túl korán

**Mitigáció:** tenant isolation és audit az alapban, SSO és central governance csak validált ügyféligény után.

---

## 16. Definition of Done

Egy funkció csak akkor tekinthető késznek, ha:

- végig működik a valódi felhasználói folyamatban;
- UI-ból használható, nem csak API-ból;
- minden üres, loading, success, error, partial és retry állapot megvan;
- authorization és tenantizoláció tesztelt;
- unit, integration, contract és releváns E2E teszt zöld;
- accessibility ellenőrzés megtörtént;
- telemetry és audit események dokumentáltak;
- migráció és rollback terv rendelkezésre áll;
- felhasználói és fejlesztői dokumentáció frissült;
- nincs dokumentált, de nem létező endpoint vagy UI-művelet.

---

## 17. Végső ajánlás

A ContentForge következő verziójának nem újabb funkciólistát, hanem bizonyíthatóan működő **brief-to-performance** folyamatot kell szállítania. Az első kiadásban a kampány-cockpit, a valós szerkesztő, a verziókezelés, a kontextusos approval és a tartós, idempotens publikálás együtt adja a termékértéket. A My Work dashboard ezt napi munkarendszerré, a Brand Governance és Localization modul pedig valódi piaci megkülönböztetővé teheti.

A konkurrencia erős az egyes részterületeken, de kevesebb termék kapcsolja össze hitelesen az AI brand governance-et, a többnyelvű kampányműködést, a platform publishingot és a teljes provenance-et. A ContentForge akkor lehet versenyképes, ha nem próbál minden eszközt helyettesíteni, hanem a többmárkás, többnyelvű, kontrollált AI content operations folyamatot teszi kiemelkedően megbízhatóvá.

---

## 18. Forrásjegyzék

### Versenytársak és termékdokumentáció

- Planable product: https://planable.io/
- Planable approvals: https://help.planable.io/hc/en-us/articles/21715462785180-Approvals-and-Approval-Workflows
- Planable pricing: https://planable.io/pricing/
- Sprout Social message approval workflows: https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows
- Sprout Social approval process: https://sproutsocial.com/insights/social-media-approval/
- Contentful localization: https://www.contentful.com/products/platform/localization-and-translation/
- Contentful localized workflows: https://www.contentful.com/help/ai-automations/workflows/localized-workflows/
- Lokalise workflow management: https://lokalise.com/product/localization-workflow-management/
- Lokalise workflows documentation: https://docs.lokalise.com/en/articles/9582608-workflows
- Lokalise developer hub: https://developers.lokalise.com/
- WRITER brand governance announcement: https://www.businesswire.com/news/home/20260528415571/en/WRITER-Solves-AIs-Brand-Governance-Crisis-with-New-Infrastructure-for-Enterprise-Marketing-at-Scale
- Frontify AI for brand management: https://www.frontify.com/en/guide/ai-for-brand-management
- Contentoo brand voice governance: https://www.contentoo.com/blog/brand-voice-governance-ai-content
- Brande.ai: https://brande.ai/

### Piaci és workflow-kutatás

- EasyContent content operations comparison: https://easycontent.io/resources/best-content-operations-platforms/
- The CMO content workflow software review: https://thecmo.com/tools/best-content-workflow-software/
- SimpleLocalize localization workflow: https://simplelocalize.io/blog/posts/what-is-a-localization-workflow/
- SimpleLocalize localization best practices: https://simplelocalize.io/blog/posts/best-practices-in-software-localization/
- Lokalise localization workflow best practices: https://lokalise.com/blog/localization-workflow-best-practices/
