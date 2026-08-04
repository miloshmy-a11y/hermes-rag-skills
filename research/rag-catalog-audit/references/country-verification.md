# Country Verification — Authoritative Check Order

When a record's `country` is wrong or missing, resolve it in THIS order. Do NOT jump
straight to keyword scanning of titles/abstracts — that is how 24 false-positive country
flags were created in one session (only 4 were real).

## Step 1 — Crossref affiliation (most reliable)
`GET https://api.crossref.org/works/<DOI>` → `message.author[].affiliation[].name`.
If an affiliation contains a country, that is the study country.
- Example: `10.1080/23311975.2022.2064405` ("...turnover...Jordan") → affiliation
  "Universiti Tenaga Nasional (UNITEN), Malaysia" → **MY**, not JO.
- Example: `10.36923/jicc.v23i2.238` ("...Despotic Leadership...Pakistan") → affiliation
  "Universiti Utara Malaysia" → **MY**, not PK.
- Example: `10.1111/jonm.13241` → "Capital University of Science & Technology,
  Islamabad, Pakistan" → **PK** (genuine).

## Step 2 — Full-text "conducted in / hospitals in" sentence
If Crossref affiliation is empty, read the methods/abstract for "conducted in X",
"hospitals in X", or an affiliation block in the PDF body.
- Example: `10.1108/lodj-07-2020-0313` → abstract "five private hospitals in
  Riyadh, Saudi Arabia" → **SA** (confirmed, despite "Saudi" only appearing as a
  keyword signal earlier).
- Example: `10.1136/bmjopen-2024-087612` → "tertiary care hospitals in Kelantan,
  Malaysia" → **MY**.
- Example: `10.1038/s41598-025-05253-0` → affiliation "King Khalid University, Abha,
  Saudi Arabia" + uses PSS-10 & ENSS → **SA**.

## Step 3 — Title is conclusive ONLY when it names the country explicitly
- `10.1016/j.ssaho.2024.100992` → title "…nurses' turnover intention in **Bangladesh**"
  → **BD** (no need for body text).

## NEVER infer country from these (false-positive traps)
- A country name appearing in a *comparison/multi-country* study's title or text
  (e.g. a cross-national study listing 20 countries → `country=None`, not any of them).
- A publisher **download/access watermark**: "Downloaded from Wiley by National
  Institutes of Health **Malaysia**" is the reader's institution, NOT the study country.
  Keep `country=None` and add `country_note` explaining.
- A **translated reprint**: e.g. the German reprint of Karasek 1979 (DOI
  `10.2307/2392498`) shows "DE" in text but the study is USA → keep `country=None`.
- A **review / meta-analysis / scoping review** that cites studies from many countries
  → `country=None` (it is not country-specific).
- `local:` tool documents (PRISMA checklist, consent forms, process-flow) → exclude
  from country auditing entirely.

## Recording a fix
Set `country=<CC>`, `country_note="<evidence>"`, `country_corrected=true`.
If genuinely unverifiable, leave `country=None` and set `needs_country_review="<why>"`
rather than guessing.
