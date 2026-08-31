# Architecture diagram — content spec

Content for the visual architecture diagram (Devpost gallery, 1920×1080 or
wider). **This spec defines content only** — boxes, arrows, labels, wording.
Styling, layout, colour and type are owned by whoever renders it.

## Title

`LastCall — how one text becomes a binding booking`
(optional subtitle: `ADK agent · Gemini 3.5 Flash on Vertex AI · Firestore · Cloud Run`)

## Boxes (7)

1. **WhatsApp — Business**
   caption: `"12 salads left, close at 9"` (one free-language text)
2. **Meta WhatsApp Cloud API**
   caption: `webhook events in · messages out`
   *(may be merged into boxes 1/6 if space is tight — then arrows go straight
   from the phones to Cloud Run)*
3. **Cloud Run — FastAPI webhook**
   caption: `acks instantly, pipeline runs in background · europe-west1`
4. **ADK agent — Gemini 3.5 Flash (Vertex AI)**
   caption: `parse → one clarifying question max → price within owner rules`
   sub-line: `wish-list matching: Gemini 3.5 Flash-Lite`
5. **Firestore**
   caption: `offers · wish lists · message log · live agent_steps`
6. **WhatsApp — Matched customers**
   caption: `"Reply YES to book — first come, first served"`
7. **Confirmations — both sides**
   caption: `winner gets pickup code · business gets binding reservation notice`

## Arrows (in flow order)

| # | From | To | Label |
|---|------|----|----|
| A | WhatsApp Business | Meta Cloud API | `one plain text` |
| B | Meta Cloud API | Cloud Run webhook | `webhook: inbound message` |
| C | Cloud Run webhook | ADK agent | `inbound event` |
| D | ADK agent | Firestore | `publish offer + log every step` |
| E | ADK agent | WhatsApp Business | `one clarifying question (only if needed)` — dashed/secondary arrow |
| F | ADK agent | WhatsApp Matched customers | `offer notification to wish-list matches` |
| G | WhatsApp Matched customers | Cloud Run webhook | `"YES"` |
| H | Firestore | Confirmations | `booking committed` |

## Callout (must appear, attached to Firestore or arrow G→H)

`first YES wins — Firestore transaction`
optional second line: `concurrent YESes can never both win`

## Wording constraints

- Model name is exactly **Gemini 3.5 Flash** (and **Flash-Lite** for matching) —
  never 2.5.
- Product names verbatim: `Cloud Run`, `Firestore`, `Vertex AI`, `ADK`,
  `Meta WhatsApp Cloud API`.
- Keep the two quoted message texts exactly as written (they match the demo).
- `agent_steps` is code-styled, lowercase with underscore.
- No stock icons or logos; all text as text (selectable/legible at 1920 wide).
- Region label `europe-west1` appears once (on Cloud Run); Vertex runs via the
  `global` endpoint — do not label Vertex with a region.
