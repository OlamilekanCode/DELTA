/**
 * Cloudflare Worker — DELTA cron dispatcher
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

    // Route by cron expression
    const endpoint =
      event.cron === "*/5 * * * *"
        ? "/api/v1/cron/refresh-crypto-quotes"
        : "/api/v1/cron/refresh-history-and-scores";

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
