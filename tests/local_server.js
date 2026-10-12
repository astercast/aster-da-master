/* tests/local_server.js — minimal Vercel routing emulator for Wave-A tests.
 * NOT shipped to production. Maps:
 *   /api/health      -> api/health.js
 *   /api/stats       -> api/stats.js
 *   /api/uploads     -> api/uploads.js
 *   /api/watch       -> api/watch.js
 *   /api/cron/signal -> api/cron/signal.js
 *   /data/v1/*.json   -> static file from data/v1/
 * Usage: node tests/local_server.js [port]   (default 3000)
 * Env: REPO_ROOT (default: parent of tests/)
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");

const REPO_ROOT = process.env.REPO_ROOT || path.join(__dirname, "..");
const PORT = Number(process.argv[2] || process.env.PORT || 3000);

const ROUTES = {
  "/api/health": "../api/health.js",
  "/api/stats": "../api/stats.js",
  "/api/uploads": "../api/uploads.js",
  "/api/watch": "../api/watch.js",
  "/api/cron/signal": "../api/cron/signal.js",
};

function makeRes(raw) {
  const headers = {};
  return {
    statusCode: 200,
    setHeader(k, v) { headers[k.toLowerCase()] = v; },
    getHeader(k) { return headers[k.toLowerCase()]; },
    end(body) {
      const h = Object.assign({ "content-length": Buffer.byteLength(body || "") }, headers);
      raw.writeHead(this.statusCode, h);
      raw.end(body || "");
    },
  };
}

const server = http.createServer((rawReq, rawRes) => {
  const u = new URL(rawReq.url, "http://localhost");
  const pathname = u.pathname;

  // static JSON under /data/v1/
  if (pathname.startsWith("/data/v1/") && pathname.endsWith(".json")) {
    const rel = pathname.replace(/^\//, ""); // data/v1/foo.json
    const abs = path.join(REPO_ROOT, rel);
    fs.readFile(abs, (e, data) => {
      if (e || !abs.startsWith(path.join(REPO_ROOT, "data", "v1"))) {
        rawRes.writeHead(404, { "content-type": "application/json" });
        rawRes.end(JSON.stringify({ ok: false }));
        return;
      }
      rawRes.writeHead(200, { "content-type": "application/json; charset=utf-8" });
      rawRes.end(data);
    });
    return;
  }

  const routeFile = ROUTES[pathname];
  if (!routeFile) {
    rawRes.writeHead(404, { "content-type": "application/json" });
    rawRes.end(JSON.stringify({ ok: false, error: { code: "NOT_FOUND", message: "no such route" } }));
    return;
  }

  // fresh require each request (mirrors cold-ish behavior; harmless locally)
  const abs = path.join(__dirname, routeFile);
  delete require.cache[require.resolve(abs)];
  let handler;
  try {
    handler = require(abs);
  } catch (e) {
    rawRes.writeHead(500);
    rawRes.end("handler load failed: " + e.message);
    return;
  }

  const req = {
    method: rawReq.method,
    headers: rawReq.headers,
    query: Object.fromEntries(u.searchParams.entries()),
    socket: rawReq.socket,
  };
  const res = makeRes(rawRes);

  let body = "";
  rawReq.on("data", (c) => { body += c; });
  rawReq.on("end", () => {
    req.body = body;
    try {
      const out = handler(req, res);
      if (out && typeof out.then === "function") {
        out.catch((e) => {
          try {
            res.statusCode = 500;
            res.setHeader("content-type", "application/json");
            res.end(JSON.stringify({ ok: false, data: null, error: { code: "INTERNAL", message: "unhandled: " + e.message } }));
          } catch (_) { /* already sent */ }
        });
      }
    } catch (e) {
      res.statusCode = 500;
      res.setHeader("content-type", "application/json");
      res.end(JSON.stringify({ ok: false, data: null, error: { code: "INTERNAL", message: "unhandled: " + e.message } }));
    }
  });
});

server.listen(PORT, () => {
  console.log("local-signal listening on http://localhost:" + PORT + " root=" + REPO_ROOT);
});
