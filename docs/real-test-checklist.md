# Real-WhatsApp end-to-end test — checklist

Goal: one real run with three phones — **your number as the business**, two
verified test recipients as customers — showing a winning YES and a too-late YES.

## A. Meta dashboard (developers.facebook.com → your app → WhatsApp)

**1. Fresh access token** — *API Setup* page → copy the temporary access token.
   - Paste it into `.env` as `WHATSAPP_ACCESS_TOKEN`.
   - Tell Claude "token is in" — redeploy to Cloud Run happens from there
     (the deploy env file is regenerated from `.env`; nothing manual).

**2. Verify the two customer numbers** — *API Setup* page → "To" recipient list
   → *Manage phone number list* → add each customer number → enter the
   verification code each phone receives. (Test numbers allow up to 5
   recipients; you as the business are already verified.)

**3. Subscribe the webhook** — *Configuration* page:
   - **Callback URL:** `https://lastcall-844499708502.europe-west1.run.app/webhook`
   - **Verify token:** the `WHATSAPP_WEBHOOK_VERIFY_TOKEN` value from `.env`
     (copy it from the file — deliberately not written here)
   - Click **Verify and save** (the handshake endpoint is deployed and tested).
   - Under **Webhook fields**, subscribe to **`messages`**. Nothing else needed.

## B. Hand Claude the two customer numbers

Send the two verified numbers (digits only, e.g. `9613xxxxxx`). They get mapped
onto seeded demo customers, wish lists arranged so BOTH match the salad offer:

| Real phone (from `.env`) | Becomes | Wish list |
|--------------------------|---------|-----------|
| `DEMO_CUSTOMER_MAYA` | **Maya** | fresh salads under $10; sushi under $15 |
| `DEMO_CUSTOMER_RAFFI` | **Raffi** | salad any price; hotel night in Jounieh under $80 |

Your own number stays the business (Sunset Deli) **only** — the dual
business+customer role it had during stub testing is removed at re-seed so your
phone doesn't get customer notifications mid-demo.

## C. Open the session windows (critical, easy to forget)

- [ ] Customer phone #1 sends **"hi"** to the LastCall test number
- [ ] Customer phone #2 sends **"hi"** to the LastCall test number
- [ ] Your business phone sends **"hi"** too (any text works)

Meta only lets the agent reply free-form inside the 24-hour window opened by
that inbound message. Each "hi" also confirms inbound webhook delivery — expect
a reply from the agent within seconds (customers get their wish-list greeting).

## D. The run (record screens from here)

1. **Business phone:** `12 salads left, close at 9`
2. Agent asks its one question → answer: `4 each`
3. Agent: published + "2 matched customer(s) notified"; both customer phones ring
4. **Customer #1 (Maya):** `YES` → 🎉 + confirmation code; business phone gets
   the binding booking notice with the same code
5. **Customer #2 (Omar):** `YES` → polite "already gone"
6. GCP console open on `agent_steps` throughout — the steps stream live

Before recording for real: `python -m app.reset` clears offers/messages/steps
(keeps businesses & customers).

## E. Afterwards

Claude saves the full message log (`python -m app.transcript`) alongside the
demo footage as the written record of the run.
