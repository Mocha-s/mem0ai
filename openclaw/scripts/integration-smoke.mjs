#!/usr/bin/env node
// Integration smoke for the V3 OSS server contract.
// Mirrors openclaw/backend/platform.ts call patterns: V3 paths,
// async-add → poll /v1/event/{id}/, /v1/events/ list, and bulk delete
// via POST /v3/memories/delete/. Run with a live mem0 server reachable
// at MEM0_BASE_URL (default http://localhost:8888).
//
//   MEM0_API_KEY=<key> node scripts/integration-smoke.mjs
//
// Exits 0 on success, non-zero on first failed step.

const BASE = process.env.MEM0_BASE_URL ?? "http://localhost:8888";
const KEY = process.env.MEM0_API_KEY ?? "mem0-admin-40901474ac3256a9d68b561b4916831eff3c32543472ed5e";
const USER = `plugin_smoke_${process.pid}_${Date.now()}`;

const stepResults = [];

function logStep(name, status, detail = "", ms = 0) {
  const tag = status === "PASS" ? "\x1b[32mPASS\x1b[0m" : "\x1b[31mFAIL\x1b[0m";
  console.log(`[${tag}] ${name} ${ms ? `(${ms}ms)` : ""} ${detail}`);
  stepResults.push({ name, status, detail, ms });
}

async function http(method, path, body) {
  const t0 = Date.now();
  const url = `${BASE}${path}`;
  const headers = { "X-API-Key": KEY };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const resp = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await resp.text();
  let json;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = text;
  }
  return { status: resp.status, body: json, ms: Date.now() - t0, url };
}

async function pollEvent(eventId, timeoutMs = 60_000) {
  // Mirrors PlatformBackend.add()'s polling: 200ms → 2s exp backoff
  const start = Date.now();
  let wait = 200;
  while (Date.now() - start < timeoutMs) {
    const ev = await http("GET", `/v1/event/${eventId}/`);
    if (ev.status !== 200) {
      throw new Error(`event poll failed: ${ev.status} ${JSON.stringify(ev.body)}`);
    }
    const status = ev.body.status;
    if (status === "SUCCEEDED") return ev.body.result;
    if (status === "FAILED") throw new Error(`event FAILED: ${ev.body.error}`);
    await new Promise((r) => setTimeout(r, wait));
    wait = Math.min(wait * 2, 2000);
  }
  throw new Error(`event ${eventId} polling timed out after ${timeoutMs}ms`);
}

async function step(name, fn) {
  const t0 = Date.now();
  try {
    const detail = await fn();
    logStep(name, "PASS", detail ?? "", Date.now() - t0);
  } catch (e) {
    logStep(name, "FAIL", e.message ?? String(e), Date.now() - t0);
    process.exitCode = 1;
    throw e;
  }
}

let memoryId; // captured during step 1

async function main() {
  console.log(`# Integration smoke against ${BASE} as user_id=${USER}`);

  await step("1. POST /v3/memories/add/ + poll until SUCCEEDED", async () => {
    const resp = await http("POST", "/v3/memories/add/", {
      messages: [
        { role: "user", content: `Plugin smoke E2E: I love jazz, my dog Rex.` },
      ],
      user_id: USER,
    });
    if (resp.status !== 200) throw new Error(`add status=${resp.status} body=${JSON.stringify(resp.body)}`);
    if (!resp.body.event_id) throw new Error(`no event_id in response: ${JSON.stringify(resp.body)}`);
    const result = await pollEvent(resp.body.event_id);
    if (!Array.isArray(result.results) || result.results.length < 1) {
      throw new Error(`no results in event: ${JSON.stringify(result)}`);
    }
    memoryId = result.results[0].id;
    return `event_id=${resp.body.event_id} → ${result.results.length} memory rows, first id=${memoryId}`;
  });

  await step("2. POST /v3/memories/ paginated list", async () => {
    const resp = await http("POST", "/v3/memories/?page=1&page_size=10", {
      filters: { user_id: USER },
    });
    if (resp.status !== 200) throw new Error(`list status=${resp.status}`);
    const { count, results, next, previous } = resp.body;
    if (typeof count !== "number") throw new Error(`count not numeric: ${count}`);
    if (!Array.isArray(results) || results.length === 0) throw new Error(`empty results`);
    if (previous !== null) throw new Error(`page=1 should have previous=null`);
    return `count=${count}, results=${results.length}, next=${next ? "set" : "null"}`;
  });

  await step("3. POST /v3/memories/search/", async () => {
    const resp = await http("POST", "/v3/memories/search/", {
      query: "music",
      filters: { user_id: USER },
    });
    if (resp.status !== 200) throw new Error(`search status=${resp.status}`);
    if (!Array.isArray(resp.body.results)) throw new Error(`no results array`);
    return `${resp.body.results.length} results, top score=${resp.body.results[0]?.score?.toFixed(3) ?? "n/a"}`;
  });

  await step("4. GET /v3/memories/{id}/", async () => {
    const resp = await http("GET", `/v3/memories/${memoryId}/`);
    if (resp.status !== 200) throw new Error(`get status=${resp.status}`);
    if (resp.body.id !== memoryId) throw new Error(`id mismatch: ${resp.body.id} vs ${memoryId}`);
    return `memory="${resp.body.memory}"`;
  });

  await step("5. PUT /v3/memories/{id}/ update", async () => {
    const resp = await http("PUT", `/v3/memories/${memoryId}/`, {
      text: "Plugin smoke updated: I love jazz and blues, my dog Rex.",
    });
    if (resp.status !== 200) throw new Error(`update status=${resp.status}`);
    return `${resp.body.message ?? "ok"}`;
  });

  await step("6. GET /v3/memories/{id}/history/", async () => {
    const resp = await http("GET", `/v3/memories/${memoryId}/history/`);
    if (resp.status !== 200) throw new Error(`history status=${resp.status}`);
    if (!Array.isArray(resp.body)) throw new Error(`history not array`);
    return `${resp.body.length} history entries (events: ${resp.body.map((h) => h.event).join("→")})`;
  });

  await step("7. POST /v3/memories/{id}/feedback/", async () => {
    const resp = await http("POST", `/v3/memories/${memoryId}/feedback/`, {
      feedback: "POSITIVE",
      feedback_reason: "smoke",
    });
    if (resp.status !== 200) throw new Error(`feedback status=${resp.status}`);
    return resp.body.message ?? "ok";
  });

  await step("8. GET /v1/events/?user_id=... — Track A endpoint", async () => {
    const resp = await http("GET", `/v1/events/?user_id=${encodeURIComponent(USER)}&limit=5`);
    if (resp.status !== 200) throw new Error(`events list status=${resp.status}`);
    const results = resp.body.results;
    if (!Array.isArray(results)) throw new Error(`results not array`);
    const succeeded = results.filter((e) => e.status === "SUCCEEDED");
    if (succeeded.length < 1) throw new Error(`expected at least 1 SUCCEEDED event for ${USER}, got 0 of ${results.length}`);
    return `${results.length} total, ${succeeded.length} SUCCEEDED for this user`;
  });

  await step("9. POST /v3/memories/delete/ bulk cleanup", async () => {
    const resp = await http("POST", "/v3/memories/delete/", {
      filters: { user_id: USER },
    });
    if (resp.status !== 200) throw new Error(`bulk delete status=${resp.status}`);
    return resp.body.message ?? "ok";
  });

  await step("10. Verify cleanup — list returns count=0", async () => {
    const resp = await http("POST", "/v3/memories/", { filters: { user_id: USER } });
    if (resp.status !== 200) throw new Error(`re-list status=${resp.status}`);
    if (resp.body.count !== 0) throw new Error(`expected count=0 after bulk delete, got ${resp.body.count}`);
    return `count=0 ✓`;
  });

  console.log("\n# Summary");
  const passed = stepResults.filter((r) => r.status === "PASS").length;
  console.log(`${passed}/${stepResults.length} steps passed`);
}

main().catch((e) => {
  console.error("\n# Aborted:", e.message ?? e);
  process.exitCode = 1;
});
