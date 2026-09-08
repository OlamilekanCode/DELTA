/**
 * Cloudflare Worker — Synthetic Exposure cron dispatcher
 *
 * Receives Cloudflare Cron Trigger events and forwards them to the
 * protected Render API endpoints with the X-Cron-Secret header.
 *
 * Required Worker secrets (set via `wrangler secret put` or the dashboard):
 *   API_BASE_URL   — e.g. https://your-api.onrender.com
 *   CRON_SECRET    — must match CRON_SECRET on the Render backend
 *
 * Deploy:
 *   npx wrangler deploy
 */

// Cron expression -> backend endpoint. Must stay in sync with the `crons`
// list in wrangler.toml — three distinct job types, each independently
// scheduled (see cloudflare/wrangler.toml for rationale).
const ROUTES = {
  "*/5 * * * *": "/api/v1/cron/refresh-crypto-quotes",
  "*/30 * * * *": "/api/v1/cron/refresh-intraday",
  "0 23 * * 2,5": "/api/v1/cron/refresh-history-and-scores",
};

export default {
  /**
   * @param {ScheduledEvent} event
   * @param {Env} env
   * @param {ExecutionContext} ctx
   */
  async scheduled(event, env, ctx) {
    const base = env.API_BASE_URL?.replace(/\/$/, "");
    const secret = env.CRON_SECRET;

    if (!base || !secret) {
      console.error("Missing API_BASE_URL or CRON_SECRET Worker secrets");
      return;
    }

    const endpoint = ROUTES[event.cron];
    if (!endpoint) {
      // Never silently fall back to a different job — an unrecognized
      // schedule string (e.g. a wrangler.toml edit without a matching
      // ROUTES entry) is a config bug that must be visible, not masked.
      console.error(`Unrecognized cron schedule "${event.cron}" — no route configured, skipping`);
      return;
    }

    ctx.waitUntil(dispatch(base, endpoint, secret));
  },
};

async function dispatch(base, endpoint, secret) {
  const url = `${base}${endpoint}`;
  let resp;
  try {
    resp = await fetch(url, {
      method: "POST",
      headers: { "X-Cron-Secret": secret, "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error(`${endpoint}: network error —`, err.message);
    return;
  }

  const body = await resp.text();
  if (resp.ok) {
    console.log(`${endpoint}: ${resp.status} ${body}`);
  } else {
    console.error(`${endpoint}: ${resp.status} ${body}`);
  }
}
