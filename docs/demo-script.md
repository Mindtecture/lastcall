# LastCall — 3-minute demo video script

Format: scene list for the HyperFrames/presenter pipeline. Each scene has a
visual, on-screen beats, and VO (plain, conversational). Target ≈ 3:00.
Primary footage: real WhatsApp screen recording + GCP console. Fallback footage:
the rendered stub transcript (`python -m app.transcript`) + `agent_steps` stream —
the same beats work for both.

---

## Scene 1 — Hook: the problem (0:00–0:25)

**Visual:** dark title card → quick cuts of closing time: stacked chairs, a deli
counter with leftover salads, a clock at 8:45pm. Text overlay: "Every night,
this becomes trash."

**VO:**
"Every night, at closing time, small businesses throw good inventory away.
Salads nobody bought. Rooms nobody booked. The owners don't have time for
dashboards or listing apps at 8:45 pm. But every single one of them has WhatsApp.
So we built LastCall — a marketplace where the only thing a business does is
send one text. Agents do everything else."

---

## Scene 2 — Business posts (live WhatsApp) (0:25–0:55)

**Visual:** phone screen recording, WhatsApp chat with LastCall.

**Beats:**
1. Business types: **"12 salads left, close at 9"** → send.
2. Agent replies within seconds: *"Got it — salads. Quick question — at what
   price each?"*
3. Business types: **"4 each"**.
4. Agent: *"✅ Published: 12x salads at $4.00, pickup until 21:00. Matching
   customers now…"* then *"📣 2 matched customer(s) notified."*

**VO:**
"This is the entire experience for a business. Free language, one message.
The agent parses it — and notice: one field was missing, so it asks exactly one
question. If three fields were missing, it would still be one question. Then it
prices within the owner's rules, publishes, and starts matching."

---

## Scene 3 — The agent thinking, live (GCP console) (0:55–1:25)

**Visual:** GCP console, Firestore `agent_steps` collection, documents appearing
in real time (split screen with the phone if possible).

**Beats:** step documents stream in: `parse` → `clarify` → `price` → `publish` →
`match` → `notify` → `notify`.

**VO:**
"Here's the same minute from the inside — this is Firestore, live in the Google
Cloud console. Every decision the agent makes is a document: it parsed the text
with Gemini on Vertex AI, asked its one question, checked the price against the
owner's minimum, published the offer, and matched it against customer wish lists.
The wish lists are free text — 'fresh salads under ten dollars' — and a
Flash-Lite model does the matching, price caps included."

---

## Scene 4 — Customer books, binding (1:25–2:05)

**Visual:** back to WhatsApp — the customer conversation.

**Beats:**
1. Customer receives: *"🔔 LastCall: Sunset Deli has 12x salads at $4.00 …
   Reply YES to book — first come, first served."*
2. Customer types: **"YES"**.
3. Agent: *"🎉 It's yours! … Confirmation code: 1672 — show it at pickup before
   21:00."*
4. Cut to business chat: *"📦 Booked: Raffi took your salads offer.
   Confirmation code XXXX — binding, they'll show it at pickup."*
5. (Quick beat) a second customer's YES: *"Sorry — that offer is already gone."*

**VO:**
"Matched customers get one message. First YES wins — and it's genuinely first:
a Firestore transaction flips the offer atomically, so two simultaneous YESes
can't both win. The winner gets a code, the business gets the same code, and
that reservation is binding. Everyone who's late gets a polite no. That's a
complete transaction — posted, matched, and sold in under two minutes, entirely
over WhatsApp."

---

## Scene 5 — Architecture (2:05–2:35)

**Visual:** one architecture slide (from README diagram): WhatsApp → Cloud Run
(FastAPI) → agent pipeline → Vertex AI Gemini + Firestore.

**VO:**
"Under the hood: a FastAPI webhook on Cloud Run receives WhatsApp events. An ADK
agent on Gemini 2.5 Flash does the parsing with a strict schema and a confidence
gate — it never guesses its way into publishing. Flash-Lite does semantic
matching. Firestore holds the offers, the message log, the live step log — and
its transactions are what make bookings binding. WhatsApp is just a thin adapter:
the same pipeline runs offline against a simulator."

---

## Scene 6 — Roadmap + close (2:35–3:00)

**Visual:** roadmap card: Reverse mode (agents bid) → Mobile app → Payments.
Final card: LastCall logo + "One text. Zero waste."

**VO:**
"Next: reverse mode — a customer says 'dinner for two under 25 tonight,' and
business agents bid for it. A mobile app for customers. Payments behind the
booking. But the core is live today: a business sends one text, and by closing
time the surplus is sold instead of thrown away. LastCall — one text, zero waste."

---

## Shot checklist (screen recordings needed)

- [ ] WhatsApp business chat: post → clarify → publish (Scene 2)
- [ ] GCP console: `agent_steps` streaming during that exact run (Scene 3)
- [ ] WhatsApp customer notification + YES + confirmation (Scene 4)
- [ ] WhatsApp business booking notice (Scene 4)
- [ ] Late-YES "already gone" (Scene 4, can be simulated via /simulate)
- [ ] Fallback if WhatsApp is down: `python -m app.transcript` render + `agent_steps`
