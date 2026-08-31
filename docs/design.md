# LastCall — v1 Design

*Hackathon: Google "All Things Agentic" (Devpost) · Track: Taskmaster · Deadline: Aug 31 2026, 5pm PT*
*Status: locked for v1 build · Last updated: Aug 25 2026*

---

## 1. What LastCall is

A last-minute offers marketplace run by AI agents. Businesses text their surplus
inventory on WhatsApp in free language ("12 salads left, close at 9"). An agent
parses the message, prices the offer **within owner-defined rules**, publishes it,
matches customer wish lists, notifies matched customers via push, takes binding
bookings, and confirms both sides — with an optional human-in-the-loop approval
step controlled by each business.

- **Businesses:** WhatsApp only. No app, no dashboard, no onboarding friction.
- **Customers:** Android-first mobile app (Expo / React Native).

---

## 2. v1 scope

### IN (must work for the demo)

1. Business texts the WhatsApp number in free language.
2. Agent parses → drafts an offer (item, tags, qty, price within owner rules, expiry).
3. **Approval gate (per-business setting `auto_publish`):**
   - `false` (default): agent sends draft back on WhatsApp — *"Reply YES to publish, or send changes"*. Business approves or revises ("make it 7") before anything goes live.
   - `true`: instant publish, confirmation after the fact.
4. Published offer → matching against customer wish lists → FCM push to matched customers.
5. Business gets WhatsApp confirmation of publication.
6. Customer books in the app → **binding booking with a 4-digit pickup code** →
   business gets WhatsApp reservation notice, customer gets in-app confirmation
   (*Moment 1 — reservation*).
7. At pickup, business texts the code to the WhatsApp number → agent marks the
   booking `completed` → both sides confirmed (*Moment 2 — pickup*).
8. **Offer expiry via Cloud Scheduler:** at `expires_at`, `published` offers →
   `expired`; their un-picked-up bookings → `expired` (neutral close, see §6).
9. **Live agent step log** (`agent_steps` collection) — every agent action written
   to Firestore in real time; the GCP-console centerpiece of the demo video.

### OUT of v1 (documented as future)

- Reverse mode — customer states intent, business agents bid (stretch goal, build step 7 only if time remains).
- Payments — booking is a reservation; pay at pickup.
- Business self-onboarding — demo businesses are pre-seeded in Firestore.
- Multi-language parsing, images, voice notes.
- Cancellations / no-show handling and reliability scoring (see §6 and §9).
- Semantic / embedding-based matching (v1 uses fixed tags).
- Customer location / "nearby" filtering (single demo city).
- iOS.

---

## 3. End-to-end workflow

```
Business WhatsApp text
   → normalize to inbound event (webhook or simulator — same shape)
   → PARSE (intent + fields, strict JSON)
   → PRICE (apply owner rules)
   → auto_publish?
        yes → PUBLISH
        no  → AWAIT_APPROVAL (WhatsApp draft → YES / revision → redraft loop)
              → PUBLISH
   → MATCH (wishlist tags) → NOTIFY (FCM push to matched customers)
   → customer BOOKS in app  ................ Moment 1: reservation
        → pickup_code issued
        → WhatsApp notice to business, in-app confirmation to customer
   → business texts pickup code  ........... Moment 2: pickup
        → booking COMPLETED, both sides confirmed
   → (else) Cloud Scheduler sweep at expiry
        → offer EXPIRED, open bookings EXPIRED (neutral close)
```

Every step above writes one document to `agent_steps` (see §4).

---

## 4. Data model (Firestore, Native mode)

```
businesses/{businessId}
  name: string
  whatsapp_number: string            # identifies inbound sender
  auto_publish: bool                 # human-in-the-loop switch
  rules: {
    min_price: int                   # cents
    max_discount_pct: int
    currency: string                 # "USD"
  }
  location: { lat: float, lng: float, area_label: string }

offers/{offerId}
  business_id: string
  item_label: string                 # "salads"
  tags: string[]                     # from fixed tag list, drives matching
  qty_total: int
  qty_left: int
  original_price: int                # cents
  offer_price: int                   # cents
  status: draft | pending_approval | published | sold_out | expired | cancelled
  expires_at: timestamp
  created_at: timestamp
  source_message: string             # raw inbound text, for traceability

customers/{customerId}               # doc id = Firebase Auth uid
  display_name: string
  fcm_token: string
  wishlist: string[]                 # same fixed tag list
  reliability: null                  # placeholder — future (§9)

bookings/{bookingId}
  offer_id: string
  business_id: string
  customer_id: string
  qty: int
  pickup_code: string                # 4-digit, unique among open bookings
  status: booked | completed | expired | cancelled
  created_at: timestamp
  completed_at: timestamp | null

agent_steps/{stepId}                 # flat, global — the live demo log
  run_id: string                     # groups the steps of one agent run
  offer_id: string | null
  business_id: string
  step: parse | price | await_approval | publish | match | notify | book | complete | expire
  detail: string                     # human-readable one-liner
  ts: timestamp
```

### Design choices

- **Tags, not free text, drive matching.** The parse agent assigns tags from a
  fixed list of ~15 (salad, pizza, sushi, burger, dessert, bakery, coffee, ...).
  Wish lists use the same list. Matching is a single Firestore
  `array-contains-any` query — fast, reliable, demoable.
- **`agent_steps` is flat** (not nested under offers) so the demo can stream one
  collection showing all agent activity live in the GCP console.
- **Money as integer cents** everywhere.
- **Statuses are the state machine.** No separate workflow engine; agents move
  documents between statuses and log each transition.

---

## 5. Message shapes & agent contract

### Inbound event (internal, source-agnostic)

The WhatsApp webhook unwraps Meta's nested payload into this; the simulator posts
it directly. Everything downstream is source-blind:

```json
{
  "from": "96171234567",
  "text": "12 salads left, close at 9",
  "ts": 1756123456,
  "source": "whatsapp" | "simulator"
}
```

### Parse agent output (Gemini, strict JSON)

```json
{
  "intent": "new_offer" | "approve" | "revise" | "pickup_code" | "unknown",
  "item_label": "salads",
  "tags": ["salad"],
  "qty": 12,
  "explicit_price": null,
  "expiry_time": "21:00",
  "code": null,
  "confidence": 0.93
}
```

- One classifier handles all inbound kinds: new offers, YES approvals,
  revisions ("make it 7"), pickup codes.
- **Low confidence or `unknown` → agent replies asking to rephrase.** It never
  guesses its way into a published offer.
- **Pricing is not the parser's job.** A separate pricing step applies owner
  rules (`max_discount_pct`, `min_price`) to an explicit price if given, or
  computes a default (e.g. 40% off original). Separate steps = separate
  `agent_steps` entries = a richer live log.

### Outbound WhatsApp messages (templates in spirit; test number, free-form session replies)

- Draft for approval: *"Draft: 12 salads at $6.00 until 21:00 — reply YES to publish, or send changes."*
- Published: *"Published: 12 salads at $6.00, until 21:00."*
- Reservation (Moment 1): *"1 salad reserved by {name}, code {code} — {n} left."*
- Pickup confirmed (Moment 2): *"{code} confirmed ✓"*

---

## 6. The `expired` status is neutral

If a business never texts the pickup code, the Scheduler closes the booking as
`expired`. This is **ambiguous by nature**: it may be a true no-show *or* a happy
pickup the business simply didn't log. v1 therefore attaches **no blame and no
reliability meaning** to `expired`; only `completed` carries positive signal.
Disambiguation is a future feature (§9).

---

## 7. WhatsApp integration strategy

- **Architecture rule: WhatsApp is a thin adapter, never the critical path.**
  The agent pipeline listens on a generic inbound endpoint; a simulator can post
  the same event shape at any time (dev, tests, demo fallback).
- Meta test number is set up and proven (hello_world delivered end-to-end from
  repo config). Test numbers allow up to 5 verified recipients — sufficient for
  the demo.
- Outbound: Cloud API `messages` endpoint; token/IDs in `.env` locally, Secret
  Manager on Cloud Run (build step 4).
- Inbound: webhook (verify token in `.env`) added in build step 4; simulator
  exists from build step 3 onward.

---

## 8. Demo beats (4-minute unedited video)

1. Phone on camera: business texts *"12 salads left, close at 9"*.
2. GCP console: `agent_steps` streaming — parse → price → await_approval.
3. Phone: draft arrives; business replies *YES*.
4. Console: publish → match → notify. Second phone / emulator: push arrives.
5. Customer app: offer visible, Book tapped → pickup code shown.
6. Phone: business gets reservation notice; texts the code back.
7. Console: booking `completed`. Both confirmations on screen.
8. (If time) auto_publish=true business: same text, zero-touch publication.

---

## 9. Future (README material)

- **Reverse mode:** customer states intent; business agents bid; customer awards.
- **Expired-booking disambiguation:** on the business's next offer message, the
  agent first asks *"Yesterday's booking 4821 — picked up or no-show?"* —
  piggybacking cleanup on a natural interaction.
- **Reliability scoring:** resolved no-shows feed a customer reliability score
  used when awarding contested offers and in reverse-mode bidding.
- **Semantic matching** (embeddings) replacing fixed tags.
- Payments, cancellations, business self-onboarding, nearby filtering, iOS,
  multi-language / media parsing.
