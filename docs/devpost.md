# LastCall — Devpost submission

**Project name:** LastCall
**Track:** Taskmaster
**One-liner:** A last-minute offers marketplace run by AI agents — businesses text
their surplus on WhatsApp, agents publish, match, and take binding bookings.

## Inspiration

In Lebanon, small businesses throw away perishable inventory every single night —
salads a deli can't keep, rooms a small hotel didn't fill, sessions a gym can't
resell. The owners are busy people closing up a shop; they will never fill in a
dashboard or manage a listings app at 8:45pm. But every one of them already uses
WhatsApp. LastCall started from one question: what if clearing tonight's surplus
took exactly one text message, and an agent did everything else?

## What it does

A business texts the LastCall number in plain language: *"12 salads left, close
at 9."* An agent parses it into a structured offer. If something essential is
missing it asks **one** clarifying question — and if several things are missing,
it asks for all of them in a single message, never an interrogation. It prices
within the owner's stored rules, publishes the offer, matches it against customer
wish lists (free text like "sushi under $15" — price caps included), and messages
every matched customer: reply YES to book. The first YES wins, atomically. The
winner gets a confirmation code, the business gets a binding reservation notice
with the same code, and everyone who was too late gets a polite "already gone."

Every step the agent takes — parse, clarify, price, publish, match, notify,
book — is written live to a Firestore `agent_steps` collection, so you can watch
the agent think in the GCP console while the WhatsApp conversation happens.

## How we built it

- **ADK (Python) + Gemini 3.5 Flash on Vertex AI** — the parse agent is an ADK
  `LlmAgent` with temperature 0 and a strict pydantic output schema. Every inbound
  business message becomes exactly one intent (`new_offer`, `revise`, `approve`,
  `pickup_code`, `unknown`) plus extracted fields. A confidence gate collapses
  anything uncertain to `unknown` — the agent never guesses its way into a
  published offer.
- **Gemini 3.5 Flash-Lite for matching** — one cheap model call judges a new offer
  against all customer wish lists at once. Because wish lists are free text,
  "fresh salads under $10" matches a $4 salad offer and correctly rejects a $12 one.
- **Firestore transactions for binding acceptance** — the first YES flips the offer
  to `taken` inside a transaction; concurrent YESes can't both win. Bookings are
  binding by construction, not by promise.
- **Cloud Run + FastAPI** — a thin webhook receives Meta WhatsApp Cloud API events,
  acks instantly, and runs the agent pipeline in the background. A `/simulate`
  endpoint posts the same event shape without Meta, so the whole pipeline runs
  offline; a stub mode logs outbound messages to Firestore instead of sending.
- **One phone, two roles** — the demo phone is both the business and a customer;
  the pipeline routes each message by conversation state, not just by sender.

## Challenges

- **Same-day dependency archaeology** — google-api-core 2.35.0 started
  percent-encoding Firestore's `(default)` database id in the gRPC routing header,
  and every write failed with a cryptic 400. Bisecting library versions on
  submission day was not the plan; pinning `<2.35` fixed it.
- **An expired Meta token mid-build** — the WhatsApp test token died before the
  final test. Because WhatsApp was designed as a thin adapter from the start, the
  stub mode + `/simulate` kept the entire agent pipeline testable end-to-end, and
  the real API drops back in with one env var.
- **Making "agentic" visible** — an agent that works silently demos badly. Writing
  every decision to a live `agent_steps` collection turned the GCP console into a
  second screen of the demo: you watch the agent parse, ask, price, publish, match
  and book in real time.
- **One clarifying question, maximum** — LLM agents love follow-up questions;
  business owners at closing time do not. Enforcing "ask for everything missing in
  one message, never two turns" took explicit pipeline state, not prompting alone.

## What's next

- **Reverse mode** — customers state intent ("dinner for two under $25 tonight"),
  business agents bid, the customer's agent awards the best offer. The marketplace
  runs agent-to-agent in both directions.
- **Customer mobile app** — Expo/React Native with FCM push, replacing WhatsApp on
  the customer side; businesses keep WhatsApp forever.
- **Payments** — a small deposit at booking time to back the binding reservation.
- **Top-N notifications** — notify the best-ranked matches instead of everyone, so an
  offer doesn't race dozens of phones at once.
- **Business pricing** — a small per-booking fee or a flat monthly line; free while the
  network grows.
- Pickup-code close-out, scheduled offer expiry, business self-onboarding, customer
  reliability scoring, embeddings-based matching at scale.

And the thesis stays the same throughout: no app to install, nothing to learn —
LastCall runs where Lebanon already talks.

## Built with

Python · ADK · Gemini 3.5 Flash / Flash-Lite · Vertex AI · Firestore · Cloud Run ·
FastAPI · Meta WhatsApp Cloud API
