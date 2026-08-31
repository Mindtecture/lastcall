# LastCall

**A last-minute offers marketplace run by AI agents — entirely on WhatsApp.**
A business texts its closing-time surplus in one plain message; an agent structures and
prices the offer, publishes it, matches customer wish lists, notifies the matches, and
takes a binding first-YES-wins booking with a pickup code. No app, no dashboard, no
onboarding — built solo for the Google **"All Things Agentic"** hackathon (Taskmaster track), Aug 2026.

## How a run looks

```
Business:  "12 salads left, close at 9"
Agent:     "Got it — salads. Quick question — at what price each?"
Business:  "4 each"
Agent:     "✅ Published: 12x salads at $4.00, pickup until 21:00. Matching customers now…"
           → notifies every customer whose wish list matches ("fresh salads under $10")
Customer:  "YES"
Agent:     "🎉 It's yours! Confirmation code: 1672 — show it at pickup before 21:00."
           → business gets the binding reservation notice with the same code
Late YES:  "Sorry — that offer is already gone. I'll keep watching your wish list."
```

If more than one essential field is missing, the agent asks for all of them in a
single message — never a 20-questions interrogation. Every agent decision is written
live to a Firestore `agent_steps` collection you can watch stream in the GCP console.

## Architecture

```
                 Meta WhatsApp Cloud API
                          │  (webhook / send)
                          ▼
              ┌───────────────────────────┐
              │   FastAPI on Cloud Run    │   europe-west1
              │  /webhook  /simulate      │
              └────────────┬──────────────┘
                           ▼
              ┌───────────────────────────┐
              │      Agent pipeline       │
              │  parse → clarify → price  │
              │  → publish → match →      │
              │  notify → book (txn)      │
              └───┬───────────────┬───────┘
                  ▼               ▼
     ┌────────────────────┐  ┌─────────────────────────┐
     │ Vertex AI (Gemini) │  │        Firestore         │
     │ 3.5 Flash: parsing │  │ businesses · customers   │
     │ (ADK LlmAgent)     │  │ offers · messages        │
     │ 3.5 Flash-Lite:    │  │ agent_steps (live log)   │
     │ wish-list matching │  │ bookings via TRANSACTION │
     └────────────────────┘  └─────────────────────────┘
```

- **Parsing** — an ADK `LlmAgent` (Gemini 3.5 Flash, temperature 0, strict pydantic
  schema) classifies every business message into one intent and extracts offer fields.
  Low confidence collapses to `unknown`; the agent never guesses its way into a
  published offer.
- **Pricing** — a separate step applies owner rules (minimum price) to the stated price.
- **Matching** — Gemini 3.5 Flash-Lite judges the offer against all wish lists in one
  call. Wish lists are free text ("sushi under $15"), so price caps and paraphrases
  match naturally.
- **Booking** — a Firestore transaction makes the first YES binding: exactly one
  commit wins, every later YES gets a polite "already gone".
- **WhatsApp is a thin adapter** — a stub mode (`WHATSAPP_STUB=1`) logs every outbound
  message to the `messages` collection instead of calling Meta, so the entire pipeline
  runs and demos offline. `/simulate` posts inbound events without Meta.

## Run it

```bash
pip install -r requirements.txt          # Python 3.11+
cp .env.example .env                     # fill in Meta + GCP values
gcloud auth application-default login    # Vertex + Firestore via ADC

python -m app.seed                       # demo businesses + customers
uvicorn app.main:app --port 8808         # local server (WHATSAPP_STUB=1 recommended)

python -m agents.run "12 salads left, close at 9"   # parse agent alone
python -m app.steps                      # agent step log
python -m app.transcript                 # rendered message transcript
python -m app.reset                      # clear demo state (keeps seeds)
```

## Testing (no WhatsApp needed)

With `WHATSAPP_STUB=1`, the full pipeline runs offline: `/simulate` plays the
role of the Meta webhook, every reply comes back in the JSON response, and all
messages/steps land in Firestore. Use your `WHATSAPP_TEST_RECIPIENT` value as
the business number; the seeded demo customers have fictional numbers.

```bash
TOKEN="$WHATSAPP_WEBHOOK_VERIFY_TOKEN"   # from your .env
BIZ="96171234567"                        # your WHATSAPP_TEST_RECIPIENT value
SIM() { curl -s -X POST localhost:8808/simulate -H "X-Verify-Token: $TOKEN" \
        -H "Content-Type: application/json" -d "{\"from\":\"$1\",\"text\":\"$2\"}"; }

# 1. Business posts an offer with a missing field -> ONE clarifying question
SIM "$BIZ" "12 salads left, close at 9"

# 2. Business answers -> priced, published, wish lists matched, customers notified
SIM "$BIZ" "4 each"

# 3. First matched customer says YES -> wins, confirmation code, business notified
SIM "96170000002" "YES"           # seeded customer Raffi ("salad any price")

# 4. Second YES -> polite "already gone" (first-YES-wins via Firestore transaction)
SIM "96170000001" "YES"           # seeded customer Maya

# 5. A customer adds a wish by chatting -> stored, confirmed in one line
SIM "96170000004" "let me know when there's pizza"

# 6. Matching pizza offer -> that customer is notified via their new wish
SIM "$BIZ" "6 pizzas at 7 each until 22:00"
```

Watch the agent think while you do this: `python -m app.steps` (or open the
`agent_steps` collection in the Firestore console), and render the whole
conversation with `python -m app.transcript`. `python -m app.reset` clears
state between test rounds.

Deploy: `gcloud run deploy lastcall --source . --region europe-west1
--allow-unauthenticated --env-vars-file .env.deploy.yaml --no-cpu-throttling`
then point the Meta webhook at `https://<service-url>/webhook` with your verify token.

> ⚠️ **Hackathon shortcut:** `/simulate` injects inbound events with only the
> webhook verify token as auth. It must be removed, or gated behind proper
> admin auth, before any post-hackathon use.

## Stack

ADK (Python) · Gemini 3.5 Flash + Flash-Lite on Vertex AI · Firestore ·
Cloud Run · FastAPI · Meta WhatsApp Cloud API

## Roadmap

- **Reverse mode / bidding** — a customer states intent ("dinner for 2 under $25
  tonight"), business agents bid, the customer's agent awards.
- **Mobile app** — Expo/React Native customer app with FCM push instead of WhatsApp.
- **Payments** — booking deposit at reservation time; today booking is binding, pay at pickup.
- **Smarter notifications** — notify the top-N best matches (ranked by wish fit and
  reliability) instead of everyone, so offers don't race dozens of phones at once.
- **Business pricing** — a small per-booking fee or a flat monthly line; free while the
  network grows.
- **Partial-quantity claims** — a customer takes just the units they want; the offer
  stays open until sold out or expired (winner-takes-all remains for single-unit
  offers like hotel rooms).
- **Self-serve wish lists** — customers set and edit wish lists in the chat itself
  (today they are seeded demo data).
- Pickup-code close-out, offer expiry sweeps, business self-onboarding, reliability
  scoring for no-shows, embeddings-based matching at scale.

> No app to install, nothing to learn — LastCall runs where Lebanon already talks.
