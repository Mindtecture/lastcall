# LastCall — CLAUDE.md

## What this project is
LastCall is a last-minute offers marketplace run by AI agents, built solo for the
Google "All Things Agentic" hackathon (Devpost, Taskmaster track, deadline Aug 31 2026 5pm PT).

Flow: businesses text surplus inventory via WhatsApp ("12 salads left, close at 9").
An agent prices within owner rules, publishes the offer, matches customer wish lists,
sends push notifications, takes a binding booking, and confirms both sides.
Customers use a mobile app (Android first). Businesses use WhatsApp only.
Stretch goal: reverse mode — customer states intent, business agents bid, customer awards.

## Stack
- Agents: ADK (Python) on Cloud Run
- Models: Gemini via Vertex AI (Flash + Flash-Lite)
- Data: Firestore (state + live agent step log), Pub/Sub, Cloud Scheduler
- Mobile: Expo / React Native, Firebase Auth, FCM push, App Distribution
- Messaging: Meta WhatsApp Cloud API (test number)
- GCP project: lastcall-hackathon, region europe-west1

## Rules & constraints
- All code written during the hackathon window (new code only)
- No secrets in the repo — tokens/keys go to Google Secret Manager or local .env (gitignored)
- 4-minute unedited live demo must show the GCP console
- Keep everything demo-oriented: simple, reliable, visible agent steps

## Working conventions
- Plain English, summary first, one step at a time
- Full new file versions, not partial edits
- Python for backend/agents, TypeScript for the Expo app
