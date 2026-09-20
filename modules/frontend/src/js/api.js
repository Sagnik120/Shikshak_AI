/**
 * Shikshak AI — API client.
 *
 * Every call hits the real backend. There is no mock fallback: if the server
 * is unreachable the UI must say so rather than show invented data.
 */

const API_BASE = `${window.location.origin}/api/v1`;

const ACCESS_KEY = "shikshak.access";
const REFRESH_KEY = "shikshak.refresh";
const USER_KEY = "shikshak.user";

/** Error carrying the HTTP status so callers can branch on it. */
export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

/* -------------------------------------------------------------------------
   Token storage
   ------------------------------------------------------------------------- */

export const tokens = {
  get access() {
    return safeGet(ACCESS_KEY);
  },
  get refresh() {
    return safeGet(REFRESH_KEY);
  },
  get user() {
    try {
      return JSON.parse(safeGet(USER_KEY) || "null");
    } catch {
      return null;
    }
  },
  save({ access_token, refresh_token, user }) {
    safeSet(ACCESS_KEY, access_token);
    safeSet(REFRESH_KEY, refresh_token);
    if (user) safeSet(USER_KEY, JSON.stringify(user));
  },
  saveUser(user) {
    safeSet(USER_KEY, JSON.stringify(user));
  },
  clear() {
    [ACCESS_KEY, REFRESH_KEY, USER_KEY].forEach((k) => {
      try {
        localStorage.removeItem(k);
      } catch {
        /* storage may be blocked; nothing to clean up */
      }
    });
  },
  get isSignedIn() {
    return Boolean(this.access && this.refresh);
  },
};

function safeGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key, value) {
  try {
    if (value === undefined || value === null) return;
    localStorage.setItem(key, value);
  } catch {
    /* private mode: the session simply won't persist across reloads */
  }
}

/* -------------------------------------------------------------------------
   Core request pipeline
   ------------------------------------------------------------------------- */

// Concurrent 401s must not each fire their own refresh, or they race and
// invalidate one another's rotated token.
let refreshInFlight = null;

async function refreshAccessToken() {
  if (refreshInFlight) return refreshInFlight;

  const refreshToken = tokens.refresh;
  if (!refreshToken) return null;

  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return null;
      const data = await response.json();
      tokens.save(data);
      return data.access_token;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

async function parseBody(response) {
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  return null;
}

function messageFor(status, body) {
  if (body && typeof body.detail === "string") return body.detail;
  if (body && Array.isArray(body.detail) && body.detail.length) {
    return body.detail[0].msg || "Invalid request.";
  }
  if (status === 0) return "Can't reach the server. Check that the backend is running.";
  if (status === 404) return "Not found.";
  if (status === 429) return "Too many attempts. Please wait a moment.";
  if (status >= 500) return "The server hit an error. Please try again.";
  return `Request failed (${status}).`;
}

async function request(path, { method = "GET", body, auth = true, isForm = false, retry = true } = {}) {
  const headers = {};
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;
  if (body && !isForm) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: isForm ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(messageFor(0), 0, null);
  }

  // One transparent refresh-and-retry when the access token has expired.
  if (response.status === 401 && auth && retry && tokens.refresh) {
    const fresh = await refreshAccessToken();
    if (fresh) {
      return request(path, { method, body, auth, isForm, retry: false });
    }
    tokens.clear();
    redirectToLogin();
    throw new ApiError("Your session expired. Please sign in again.", 401, null);
  }

  const data = await parseBody(response);

  if (!response.ok) {
    throw new ApiError(messageFor(response.status, data), response.status, data);
  }
  return data;
}

function redirectToLogin() {
  const here = window.location.pathname + window.location.search;
  const onAuthPage = /\/(login|signup|verify|forgot|reset|index)?\.?html?$/.test(
    window.location.pathname
  );
  if (onAuthPage && !window.location.pathname.includes("dashboard")) return;
  window.location.href = `/login.html?next=${encodeURIComponent(here)}`;
}

/* -------------------------------------------------------------------------
   Endpoints
   ------------------------------------------------------------------------- */

export const api = {
  baseUrl: API_BASE,

  // --- auth ---
  signup: (payload) => request("/auth/signup", { method: "POST", body: payload, auth: false }),
  verifyEmail: (email, code) =>
    request("/auth/verify-email", { method: "POST", body: { email, code }, auth: false }),
  resendOtp: (email, purpose = "verify_email") =>
    request("/auth/resend-otp", { method: "POST", body: { email, purpose }, auth: false }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  forgotPassword: (email) =>
    request("/auth/forgot-password", { method: "POST", body: { email }, auth: false }),
  resetPassword: (email, code, newPassword) =>
    request("/auth/reset-password", {
      method: "POST",
      body: { email, code, new_password: newPassword },
      auth: false,
    }),
  me: () => request("/auth/me"),

  async logout() {
    const refresh = tokens.refresh;
    if (refresh) {
      try {
        await request("/auth/logout", { method: "POST", body: { refresh_token: refresh }, auth: false });
      } catch {
        /* the local session is cleared regardless */
      }
    }
    tokens.clear();
  },

  // --- account ---
  getProfile: () => request("/account/profile"),
  updateProfile: (payload) => request("/account/profile", { method: "PATCH", body: payload }),
  changePassword: (currentPassword, newPassword) =>
    request("/account/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    }),
  listSessions: () => request("/account/sessions"),
  revokeSession: (id) => request(`/account/sessions/${id}`, { method: "DELETE" }),
  revokeAllSessions: () => request("/account/sessions/revoke-all", { method: "POST" }),
  deleteAccount: (password) =>
    request("/account/", { method: "DELETE", body: { password, confirm: "DELETE" } }),

  // --- documents ---
  uploadDocument(file, onProgress) {
    // XHR rather than fetch, because upload progress needs it.
    return new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/lessons/documents`);
      xhr.setRequestHeader("Authorization", `Bearer ${tokens.access}`);

      xhr.upload.onprogress = (event) => {
        if (onProgress && event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      xhr.onload = () => {
        let data = null;
        try {
          data = JSON.parse(xhr.responseText);
        } catch {
          /* handled below */
        }
        if (xhr.status >= 200 && xhr.status < 300) resolve(data);
        else reject(new ApiError(messageFor(xhr.status, data), xhr.status, data));
      };
      xhr.onerror = () => reject(new ApiError(messageFor(0), 0, null));
      xhr.send(form);
    });
  },
  listDocuments: () => request("/lessons/documents"),
  deleteDocument: (id) => request(`/lessons/documents/${id}`, { method: "DELETE" }),

  // --- lessons ---
  createLesson: (payload) => request("/lessons", { method: "POST", body: payload }),
  generatePlan: (lessonId) => request(`/lessons/${lessonId}/plan`, { method: "POST" }),
  getLesson: (lessonId) => request(`/lessons/${lessonId}`),
  deleteLesson: (lessonId) => request(`/lessons/${lessonId}`, { method: "DELETE" }),
  getWsTicket: (lessonId) => request(`/lessons/${lessonId}/ticket`, { method: "POST" }),
  listLessons(params = {}) {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );
    const suffix = query.toString() ? `?${query}` : "";
    return request(`/lessons${suffix}`);
  },

  // --- insights ---
  dashboard: () => request("/dashboard"),
  analytics: () => request("/analytics"),
  learningProfile: () => request("/profile/learning"),

  /**
   * Authenticated media needs its Authorization header, so it can't go
   * straight into a <video src>. Fetch it and hand back an object URL.
   */
  /** Download the lesson's notes as a Markdown file the learner can keep. */
  async downloadNotes(lessonId, title) {
    const response = await fetch(
      `${API_BASE}/lessons/${encodeURIComponent(lessonId)}/notes?format=markdown&download=true`,
      { headers: { Authorization: `Bearer ${tokens.access}` } },
    );
    if (!response.ok) throw new ApiError("Could not build your notes.", response.status, null);
    const blob = await response.blob();
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `${(title || "lesson").replace(/[^\w \-]/g, "").slice(0, 80)} - notes.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Revoked on the next tick so the download has already started.
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  },

  lessonNotes(lessonId) {
    return request(`/lessons/${encodeURIComponent(lessonId)}/notes`);
  },

  async mediaObjectUrl(url) {
    const response = await fetch(url.startsWith("http") ? url : `${window.location.origin}${url}`, {
      headers: { Authorization: `Bearer ${tokens.access}` },
    });
    if (!response.ok) throw new ApiError("Could not load the video.", response.status, null);
    return URL.createObjectURL(await response.blob());
  },
};

/** Open the live classroom socket for a lesson, using a short-lived ticket. */
export async function openLessonSocket(lessonId) {
  const { ticket, ws_path } = await api.getWsTicket(lessonId);
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const url = `${scheme}://${window.location.host}${ws_path}?ticket=${encodeURIComponent(ticket)}`;
  return new WebSocket(url);
}
