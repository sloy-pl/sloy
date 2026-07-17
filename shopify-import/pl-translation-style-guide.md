# PL Translation Style Guide (sloy.pl)

Based on comparing `translations_pl.csv` EN/PL pairs across product titles, descriptions, meta descriptions, product types, and handles. The Polish version is **not a literal translation** — it's a rewrite for a Polish vintage-design audience, generally more compact than the English.

For review with the translator/author: flag anything below that doesn't match intent, so it can be codified before translating new strings.

## 1. General principle: adapt, don't translate literally

The PL text consistently drops, reorders, or compresses info rather than mirroring EN sentence-by-sentence. Treat EN copy as source material, not a script to follow line-for-line.

- EN: "Iconic Zen armchair in vibrant orange Alcantara by Claude Brisson for Ligne Roset, France 1980s. Ergonomic contoured seat, flexible frame, adjustable headrest."
- PL: "Pomarańczowy fotel Zen, Claude Brisson dla Ligne Roset, lata 80. Giętka konstrukcja, oryginalna tkanina Alcantara. Klasyka francuskiego designu. Wys. 104 cm."

Note PL drops "Ergonomic contoured seat," adds "Klasyka francuskiego designu" (not in EN) and a dimension. This kind of substitution — cut a generic claim, add a concrete/local detail — is the norm, not an error.

**Watch for kalki językowe (calques) and false friends.** Don't translate EN idioms or phrase structures word-for-word into Polish patterns that a native speaker wouldn't naturally produce — rewrite for how a Polish copywriter would actually phrase it, not a literal mirror of the English syntax. Flag/avoid known false friends (e.g. "eventually" ≠ "ewentualnie", "actual" ≠ "aktualny") and generic English marketing constructions that read as translated rather than native when rendered literally in Polish.

**Vary the wording (synonimizacja) across similar products/descriptions rather than reusing the same phrases verbatim every time** — this is a deliberate SEO move to capture more organic search variety, not an inconsistency to fix. Prefer swapping in synonyms for recurring descriptive terms (materials, condition, style adjectives) between listings rather than copy-pasting the same phrasing.

## 2. Titles

**Structure:** `[Product type] [Designer/Brand] [Model name] | [Origin], [decade]` — product type usually leads in PL, whereas EN often leads with designer/brand name.

- EN: `Luigi Colani UFO floor lamp – Wofi Leuchten | space age 1970s`
- PL: `Lampa podłogowa UFO Luigi Colani – Wofi Leuchten | space age lata 70.`

- EN: `Richard Sapper Tizio Terra floor lamp | Artemide Italy 1972`
- PL: `Lampa podłogowa Richard Sapper Tizio Terra | Artemide, Włochy 1972`

**Decades:** EN `1970s` → PL `lata 70.` (with trailing period; "XX wieku" is sometimes appended in longer copy but not usually in titles). Confirmed with translator: this is a free choice, not a rule — either form is fine, pick whichever reads better in context.

**Punctuation:** EN commonly uses `–` (en dash) or `|` before origin/period; PL sometimes converts dashes to commas (`Fotele Hestra, Tord Bjorklund, IKEA | postmodernizm, 1991`) — no fixed rule observed, translator seems to pick whichever reads more naturally in Polish.

**Country names:** always translated (`Germany` → `Niemcy`, `Italy` → `Włochy`, `France` → `Francja`, `Denmark` → `Dania`, `Poland` → `Polska`). `West Germany` is sometimes simplified to `Niemcy`.

**Designer names:** in Polish copy, always **keep original diacritics** (`Tord Björklund`, `Søholm`) — this is intentional, not an oversight. The translator does sometimes drop diacritics elsewhere (e.g. in the site's dropdown/navigation menu and "about the company" text), but that's a separate, deliberate choice for those specific contexts — it does not apply to product titles/descriptions.

## 3. Product descriptions (body_html)

**Length: PL is consistently shorter than EN — often by 30–50%.** The translator cuts filler/marketing language and keeps concrete facts (materials, dimensions, condition, provenance).

Phrases that get cut almost every time in PL:
- "exemplif[ies/y] [style] design of the [decade]" — generic art-historical framing, usually dropped or replaced with a terser phrase.
- "making it suitable for..." / "ideal for..." lifestyle-use suggestions — sometimes kept, often trimmed to one clause.
- Redundant adjective stacking ("bold geometric composition that plays with light and shadow") gets reduced to one or two adjectives.

Example of typical compression:
- EN: "The organic, flowing forms and volcanic texture exemplify West German ceramic art of the 1970s. Each sconce casts dramatic shadows and ambient light, making them both functional lighting and decorative wall sculptures."
- PL: "Kinkiety pięknie odbijają i rozpraszają światło, pełniąc jednocześnie rolę oświetlenia i rzeźby ściennej."

**Tone:** PL is warmer/more direct, occasionally more colloquial than EN's museum-catalog tone. E.g. EN "creates a soft glow when lit" → PL "po włączeniu zapewnia wyjątkowe wrażenia" (more evocative, less descriptive-literal).

**Rhetorical hooks are kept when present in EN** (e.g. "Can a piece of furniture be a landscape?", "For the dog lovers, stamp collectors...") — these openers are translated closely, not cut, since they carry brand voice.

**HTML structure/markup** (`<p>`, `<strong>`, inline styles) is preserved as-is; only text content changes. Don't alter tags/classes during translation.

## 4. Meta descriptions

Same compression pattern as body copy, even more aggressive — PL meta descriptions frequently drop a whole clause EN includes (e.g. condition note, a dimension, or a "suitable for" clause), presumably to fit length constraints.

- EN: "Alburette coffee table by Albert Busch, Germany 1960s. Compact cubic design with glass top and brass edge. Good vintage condition, professionally inspected."
- PL: "Stolik kawowy Alburette Albert Busch, Niemcy lata 60. Kompaktowa forma ze szklanym blatem i mosiężną krawędzią." *(condition sentence dropped entirely)*

Confirmed with client: dropping clauses is an acceptable space-saving move for new strings, but where possible **prefer keeping key facts (condition, dimensions)** for consistency across listings rather than cutting them by default.

Condition/inspection phrasing is **intentionally varied** — this is not an inconsistency to fix. Do not standardize to one fixed phrase per tier; keep rotating between variants such as:
- "Electrically tested" → "Sprawdzona elektrycznie" / "Testowana elektrycznie"
- "Professionally tested" / "Professionally inspected" → "Po przeglądzie elektrycznym" / "Po kompleksowym przeglądzie elektrycznym"
- "Excellent condition" → "Doskonały stan" / "Stan idealny"
- "Good vintage condition" → "Dobry stan vintage" / "Stan dobry"

## 5. Product type (category label)

Direct, literal translation, always short noun phrases — no compression needed here since these are already minimal:

| EN | PL |
|---|---|
| Floor Lamp | Lampa podłogowa |
| Desk Lamp / Task Lamp | Lampa biurkowa |
| Wall Sconce | Kinkiet |
| Pendant Lamp | Oświetlenie sufitowe / Lampa wisząca |
| Coffee Table | Stolik kawowy |
| Lounge Chair | Fotel wypoczynkowy |
| Armchair | Fotel |
| Ottoman | Siedzisko |
| Candleholder | Świecznik |
| Night Light | Lampka nocna |
| Decorative Plate | Talerz dekoracyjny |
| Decorative Bowl | Miska dekoracyjna |
| Wall Sculpture | Rzeźba ścienna |
| Vase | Wazon |
| Tray | Taca |
| Desk Organizer | Organizer na biurko |
| Ashtray | Popielniczka |

Confirmed: "Wall Sconce" → "Kinkiet" (unchanged), but **"Pendant Lamp" should be "Oświetlenie sufitowe" / "Lampa wisząca"** — these are distinct fixtures and must not be collapsed into "Kinkiet".

## 6. Handles (URL slugs)

Same reordering as titles: PL slug tends to lead with product type where the title does, drops the decade/origin sometimes, and always strips Polish diacritics (ł→l, ą→a, etc. — required for valid URLs).

- EN: `luigi-colani-ufo-floor-lamp-wofi-leuchten-1970s`
- PL: `lampa-podlogowa-luigi-colani-wofi-leuchten-space-age-lata-70`

No fixed rule for exact word order beyond "product type first if it leads the PL title." Translator seems to freely rewrite the slug rather than transliterate the EN one word-for-word.

## 7. Numbers, units, measurements

- Metric units kept as-is (`cm`), always with a **hard (non-breaking) space** between the number and unit — `73 cm`, `36 cm wysokości` — so the number and unit never break across lines. Use `&nbsp;` (or the equivalent non-breaking space character) between the digits and `cm`, not a regular space.
- "Set of 2" → "2 szt." / "zestaw 2 szt." / "para" (varies by context — "para" (pair) preferred for two matching sconces/lamps, "zestaw" for mixed sets, "szt." in meta descriptions).

## 8. Vocabulary / false-friend glossary

- **Glaze → always "szkliwo"** (ceramics glaze), never "glazura" (which reads as bathroom/floor tiling in Polish — a false friend introduced by MT tools). Applies to all forms: "glazed" → "szkliwiony/a/e", "glazing" → "szkliwienie".

## Resolved (client feedback, 2026-07)

1. Decade format: `lata 70.` vs `lata 70. XX wieku` — no fixed rule, either is fine; translator's call.
2. Diacritics in designer names — always kept in Polish copy (see §2). Dropped only in the site's nav dropdown/company-description context, which is a separate deliberate choice.
3. Condition-phrase tiers — intentionally varied, not to be standardized to one fixed phrase.
4. "Kinkiet" vs pendant lamp — split: "Kinkiet" is wall sconce only; pendant lamp is "Oświetlenie sufitowe" / "Lampa wisząca" (see §5).
5. Compression — dropping clauses in new strings is acceptable, but prefer retaining key facts (condition, dimensions) for consistency where space allows.
