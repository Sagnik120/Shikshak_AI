// Where the backend lives. Empty = same origin as this page (local runs and the
// single-container deploy). A split deploy (frontend on Vercel, backend on a
// container host) overwrites this file at build time — see modules/frontend/vercel.json.
export const BACKEND_ORIGIN = "";
