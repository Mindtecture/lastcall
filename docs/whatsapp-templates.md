# WhatsApp message templates (production)

The hackathon demo runs entirely on **session messages**: a customer or business
texts the LastCall number first, which opens Meta's 24-hour customer-service
window, and inside that window the agent may reply with free-form text — no
template needed. That is why the demo checklist has every participant send "hi"
before the run.

**Templates are required the moment LastCall initiates**: any business-initiated
message sent outside the 24-hour window since that person's last inbound message
must be a pre-approved template. In production, offer notifications are exactly
that case — a customer may not have texted us for days when a matching offer
appears. The three templates below cover the notification flow; they would be
submitted for approval in Meta Business Manager before launch.

---

## 1. `offer_notification` — category: MARKETING

*When:* a new offer matches a customer's wish list and their session window is
closed (the common case). This is promotional content initiated by us, so Meta
classifies it as Marketing and the customer must have opted in (they did, by
creating a wish list).

```
🔔 LastCall: {{1}} has {{2}}x {{3}} at {{4}}, pickup until {{5}} — it matched
your wish list ("{{6}}"). Reply YES to book. First come, first served.
```

| Var | Meaning | Example |
|-----|---------|---------|
| {{1}} | business name | Sunset Deli |
| {{2}} | quantity | 12 |
| {{3}} | item | salads |
| {{4}} | unit price | $4.00 |
| {{5}} | pickup deadline | 21:00 |
| {{6}} | the wish that matched | fresh salads under $10 |

A customer's "YES" reply re-opens their 24-hour window, so everything after the
notification (confirmation or sold-out notice) can be free-form — but the
templates below exist for the edge where confirmation must be re-sent later.

## 2. `booking_confirmation` — category: UTILITY

*When:* re-sending or recovering a confirmation outside the customer's window
(e.g. a reminder shortly before the pickup deadline). Transactional follow-up to
an action the customer took → Utility.

```
✅ Booking confirmed: {{1}}x {{2}} from {{3}} at {{4}}. Your confirmation code
is {{5}} — show it at pickup before {{6}}. This reservation is binding.
```

| Var | Meaning | Example |
|-----|---------|---------|
| {{1}} | quantity | 12 |
| {{2}} | item | salads |
| {{3}} | business name | Sunset Deli |
| {{4}} | unit price | $4.00 |
| {{5}} | confirmation code | 1672 |
| {{6}} | pickup deadline | 21:00 |

## 3. `sold_out_notice` — category: UTILITY

*When:* closing the loop with notified customers after an offer is taken or
expires, if their window has closed. Status update about an interaction they
were part of → Utility.

```
The {{1}} offer from {{2}} is gone — someone beat you to it. Your wish list
stays active and we'll message you the moment something else matches.
```

| Var | Meaning | Example |
|-----|---------|---------|
| {{1}} | item | salads |
| {{2}} | business name | Sunset Deli |

---

**Business side needs no templates in practice:** businesses message us first
every time they post an offer, so the 24-hour session window is always open for
the whole clarify → publish → booking-notice exchange. The one production
exception would be a booking notice arriving more than 24h after the business's
last text — unlikely for same-evening offers, but `booking_confirmation` can be
reused for it.
