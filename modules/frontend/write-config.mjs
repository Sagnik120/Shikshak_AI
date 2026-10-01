// Vercel build step: point the static frontend at the backend.
// Set SHIKSHAK_BACKEND_URL in the Vercel project (e.g. https://you-shikshak.hf.space).
import { writeFileSync } from "node:fs";

const raw = (process.env.SHIKSHAK_BACKEND_URL || "").trim().replace(/\/+$/, "");
let url;
try {
  url = new URL(raw);
} catch {
  console.error("SHIKSHAK_BACKEND_URL is missing or not a URL. Set it in Vercel → Settings → Environment Variables.");
  process.exit(1);
}
if (url.protocol !== "https:" && url.hostname !== "localhost") {
  console.error(`SHIKSHAK_BACKEND_URL must be https (got ${raw}); browsers block ws:// and http:// from an https page.`);
  process.exit(1);
}

writeFileSync(
  new URL("./src/js/config.js", import.meta.url),
  `// Generated at build time by write-config.mjs — do not edit.\nexport const BACKEND_ORIGIN = ${JSON.stringify(url.origin)};\n`,
);
console.log(`Frontend will talk to ${url.origin}`);
