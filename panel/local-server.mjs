/**
 * Self-hosted adapter. Node.js >=22 with built-in node:sqlite.
 * Loopback listener: use an HTTPS reverse proxy in production.
 */
import { createServer } from "node:http";
import { DatabaseSync } from "node:sqlite";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import panel from "./worker.js";

const here = dirname(fileURLToPath(import.meta.url));
const dbfile = resolve(process.env.SQLITE_PATH || "./panel-data/panel.sqlite");
mkdirSync(dirname(dbfile), { recursive: true });
const db = new DatabaseSync(dbfile);
db.exec(readFileSync(resolve(here, "schema.sql"), "utf8"));

function d1(database) {
  return {
    prepare(sql) {
      let params = [];
      return {
        bind(...args) { params = args; return this; },
        async first() { return database.prepare(sql).get(...params) || null; },
        async all() { return { results: database.prepare(sql).all(...params) }; },
        async run() {
          const result = database.prepare(sql).run(...params);
          return { success: true, meta: { changes: result.changes } };
        }
      };
    }
  };
}
const env = {
  DB: d1(db),
  ADMIN_PASS_HASH: process.env.ADMIN_PASS_HASH,
  SESSION_KEY: process.env.SESSION_KEY,
  ENCRYPTION_KEY: process.env.ENCRYPTION_KEY
};
if (!env.ADMIN_PASS_HASH || !env.SESSION_KEY || !env.ENCRYPTION_KEY)
  throw new Error("Configure ADMIN_PASS_HASH, SESSION_KEY e ENCRYPTION_KEY antes de iniciar.");
const port = Number(process.env.PORT || 8787);
const origin = process.env.PUBLIC_ORIGIN || "http://127.0.0.1:" + port;
new URL(origin);
const server = createServer(async (req, res) => {
  try {
    const chunks = [];
    let bytes = 0;
    for await (const chunk of req) {
      bytes += chunk.length;
      if (bytes > 22000) {
        res.writeHead(413).end("Payload too large");
        return;
      }
      chunks.push(chunk);
    }
    const url = new URL(req.url || "/", origin).href;
    const headers = new Headers();
    for (const [name, value] of Object.entries(req.headers)) {
      if (Array.isArray(value)) headers.set(name, value.join(", "));
      else if (value !== undefined) headers.set(name, value);
    }
    const payload = Buffer.concat(chunks);
    const request = new Request(url, {
      method: req.method,
      headers,
      body: ["POST", "PUT", "PATCH"].includes(req.method) ? payload : undefined
    });
    const response = await panel.fetch(request, env);
    res.statusCode = response.status;
    response.headers.forEach((value, key) => res.setHeader(key, value));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch {
    res.writeHead(500, { "content-type": "application/json" }).end('{"error":"Falha interna"}');
  }
});
server.listen(port, "127.0.0.1", () => console.log("ArtiSys Panel em 127.0.0.1:" + port + "; origem: " + origin));
