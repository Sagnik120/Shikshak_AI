/**
 * The live classroom, framework-free. A port of the original classroom.js
 * protocol: it drives the teaching WebSocket, owns the <video> element's
 * checkpoint gating, and publishes an immutable UI snapshot that React
 * subscribes to with useSyncExternalStore.
 *
 * Guarantees kept from the original:
 *  - answers carry interaction_id, so a stale answer can never grade another question
 *  - the video can't play or seek past an unanswered checkpoint
 *  - a reconnect never restarts a loaded video or wipes a typed answer
 *  - a paused (escalated) lesson never auto-starts
 */
import { api, wsUrl, ApiError } from "@/core/api";
import type { Citation, EvaluationEvent, InteractionEvent, LessonDetail, SavedNote } from "@/core/types";
import type { MessageKey } from "@/core/i18n";

export type Connection = "connecting" | "live" | "reconnecting" | "offline" | "paused" | "unavailable" | "elsewhere" | "done";

export type NodeView = {
  node_id: string; concept: string; status: string; attempts: number;
  video_url: string | null; checkpoint_question?: boolean;
};

export type Overlay =
  | { kind: "loading"; title: string; bodyKey: MessageKey }
  | { kind: "text"; title: string; body: string }
  | { kind: "error"; titleKey: MessageKey; body: string; redirect?: string }
  | { kind: "paused"; concept: string }
  | { kind: "review"; concepts: Array<{ node_id: string; concept: string }> }
  | { kind: "complete"; score: number }
  | { kind: "elsewhere" }
  | { kind: "offline" };

export type NotesView = {
  node_id: string; concept: string; depth?: string; est_minutes?: number;
  formula?: string; points: string[]; example?: string; transcript: string;
};

export type QaEntry = { question: InteractionEvent; answer?: string; result?: EvaluationEvent };

export type CitationView = (Citation & { attempts?: number; refined_query?: string; none?: boolean }) | null;

export type ClassroomState = {
  title: string;
  connection: Connection;
  statusKey: MessageKey | null;
  nodes: NodeView[];
  currentNodeId: string | null;
  progress: { pct: number; done: number; total: number };
  overlay: Overlay | null;
  question: InteractionEvent | null;
  grading: boolean;
  feedback: EvaluationEvent | null;
  feedbackFor: string | null;
  qa: QaEntry[];
  notes: NotesView | null;
  collected: Array<{ node_id: string; concept: string; points: string[]; example?: string }>;
  citation: CitationView;
  isDocument: boolean;
  adaptation: { action: "MODIFY" | "REGENERATE" | "HUMAN"; slow: boolean } | null;
  videoVisible: boolean;
  stopped: boolean;
  log: Array<{ at: number; text: string }>;
  checkpoints: { total: number; passed: number };
  toast: { id: number; key: MessageKey; tone: "info" | "success" | "warning" | "error"; raw?: string } | null;
};

const MAX_RECONNECT = 8;
const CLOSE_SUPERSEDED = 4001;
const CLOSE_POLICY = 1008;

type Segment = {
  node_id: string; video_url: string | null;
  checkpoints: Array<{ index: number; at_sec: number }>;
  passed: Set<number>; awaiting: number | null; done: boolean; sent: boolean;
};

const GREEK: Record<string, string> = {
  "\\Sigma": "Σ", "\\sum": "Σ", "\\Delta": "Δ", "\\delta": "δ", "\\alpha": "α", "\\beta": "β", "\\theta": "θ",
  "\\pi": "π", "\\mu": "μ", "\\omega": "ω", "\\cdot": "·", "\\times": "×", "\\div": "÷", "\\pm": "±",
  "\\approx": "≈", "\\leq": "≤", "\\geq": "≥", "\\neq": "≠", "\\rightarrow": "→", "\\infty": "∞",
};

/** LaTeX → readable text; a backslash must never reach the page. */
export function plainMath(raw: unknown) {
  let s = String(raw || "").trim();
  s = s.replace(/```[a-z]*|```/g, "").replace(/^latex:\s*/i, "").replace(/\\\\/g, "\\");
  s = s.replace(/^\$\$|\$\$$/g, "").replace(/^\$|\$$/g, "");
  s = s.replace(/\\\(([\s\S]*?)\\\)/g, "$1").replace(/\\\[([\s\S]*?)\\\]/g, "$1");
  s = s.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "($1)/($2)");
  s = s.replace(/\\vec\s*\{([^{}]*)\}/g, "$1⃗").replace(/\\(?:text|mathrm)\s*\{([^{}]*)\}/g, "$1");
  for (const [tex, glyph] of Object.entries(GREEK)) s = s.split(tex).join(glyph);
  return s.replace(/\\[a-zA-Z]+/g, "").replace(/[{}]/g, "").replace(/\s+/g, " ").trim();
}

export function sentenceFallback(script: unknown) {
  return String(script || "").split(/(?<=[.!?।])\s+/).map((s) => s.trim()).filter(Boolean).slice(0, 4);
}

/* eslint-disable @typescript-eslint/no-explicit-any */
type Payload = Record<string, any>;

export class ClassroomController {
  private state: ClassroomState;
  private listeners = new Set<() => void>();
  private socket: WebSocket | null = null;
  private video: HTMLVideoElement | null = null;
  private seg: Segment | null = null;
  private objectUrls: string[] = [];
  private closedByUs = false;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeat: ReturnType<typeof setInterval> | null = null;
  private adaptationTimer: ReturnType<typeof setTimeout> | null = null;
  private lastAdaptationKey: string | null = null;
  private questionShownAt = 0;
  private lastError: string | null = null;
  private toastId = 0;
  private disposed = false;
  /** Set while the rewatch dialog is open: live playback must wait. */
  rewatchOpen = false;
  private resumeAfterRewatch = false;

  constructor(private lessonId: string, private onNavigate: (href: string) => void) {
    this.state = {
      title: "", connection: "connecting", statusKey: "class.connecting", nodes: [], currentNodeId: null,
      progress: { pct: 0, done: 0, total: 0 }, overlay: null, question: null, grading: false, feedback: null,
      feedbackFor: null, qa: [], notes: null, collected: [], citation: null, isDocument: false, adaptation: null,
      videoVisible: false, stopped: false, log: [], checkpoints: { total: 0, passed: 0 }, toast: null,
    };
  }

  /* -- store ------------------------------------------------------------ */
  subscribe = (fn: () => void) => { this.listeners.add(fn); return () => { this.listeners.delete(fn); }; };
  getSnapshot = () => this.state;
  private set(patch: Partial<ClassroomState>) {
    if (this.disposed) return;
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((l) => l());
  }
  private logLine(text: string) { this.set({ log: [...this.state.log.slice(-80), { at: Date.now(), text }] }); }
  private toast(key: MessageKey, tone: "info" | "success" | "warning" | "error" = "info", raw?: string) {
    this.set({ toast: { id: ++this.toastId, key, tone, raw } });
  }
  private overlay(o: Overlay | null) {
    this.set({ overlay: o });
    if (o && o.kind !== "loading") this.video?.pause();
  }

  /* -- lifecycle -------------------------------------------------------- */
  async start() {
    try {
      const lesson = await api.getLesson(this.lessonId);
      this.applyLesson(lesson);
      if (lesson.status === "completed" && !lesson.review_pending) return this.onNavigate(`/report/${this.lessonId}`);
      if (lesson.status === "escalated") {
        this.set({ stopped: true, connection: "paused", statusKey: "class.paused" });
        return this.overlay({ kind: "paused", concept: lesson.escalation?.concept || "" });
      }
      this.connect();
    } catch (e) {
      this.set({ connection: "unavailable" });
      this.overlay({ kind: "error", titleKey: "class.couldNotStart", body: (e as Error).message, redirect: e instanceof ApiError && e.status === 404 ? "/new" : undefined });
    }
    this.heartbeat = setInterval(() => this.send("ping", {}), 25000);
    window.addEventListener("online", this.onOnline);
  }

  dispose() {
    this.disposed = true;
    this.closedByUs = true;
    if (this.heartbeat) clearInterval(this.heartbeat);
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.adaptationTimer) clearTimeout(this.adaptationTimer);
    window.removeEventListener("online", this.onOnline);
    this.detachVideo();
    this.socket?.close();
    this.objectUrls.forEach((u) => URL.revokeObjectURL(u));
  }

  private applyLesson(lesson: LessonDetail) {
    this.set({
      title: lesson.title,
      isDocument: lesson.source === "document",
      nodes: lesson.nodes.map((n) => ({ node_id: n.node_id, concept: n.concept, status: n.status, attempts: n.attempts, video_url: n.video_url })),
      progress: { pct: lesson.progress_pct, done: lesson.nodes_completed, total: lesson.node_count },
      collected: lesson.nodes.filter((n) => n.script_text || n.notes).map((n) => ({
        node_id: n.node_id, concept: n.concept,
        points: (n.notes?.key_points || []).filter(Boolean).length ? n.notes!.key_points! : sentenceFallback(n.script_text).slice(0, 3),
        example: n.notes?.example || undefined,
      })),
      qa: lesson.nodes.flatMap((n) => n.interactions.filter((i) => i.raw_answer != null).map((i) => ({
        question: { interaction_id: i.id, node_id: n.node_id, question_text: i.question_text, type: i.question_type, options: i.options },
        answer: i.raw_answer ?? undefined,
        result: { node_id: n.node_id, correct: !!i.correct, partial_credit: i.partial_credit, feedback_text: i.feedback_text || "", misconception_tag: i.misconception_tag },
      }))),
    });
  }

  /* -- video ------------------------------------------------------------ */
  attachVideo(v: HTMLVideoElement | null) {
    if (v === this.video) return;
    this.detachVideo();
    this.video = v;
    if (!v) return;
    v.addEventListener("timeupdate", this.onTime);
    v.addEventListener("play", this.onPlay);
    v.addEventListener("seeking", this.onSeeking);
    v.addEventListener("ended", this.onEnded);
  }
  private detachVideo() {
    const v = this.video;
    if (!v) return;
    v.removeEventListener("timeupdate", this.onTime);
    v.removeEventListener("play", this.onPlay);
    v.removeEventListener("seeking", this.onSeeking);
    v.removeEventListener("ended", this.onEnded);
    this.video = null;
  }
  private nextCheckpoint() {
    const s = this.seg;
    return s?.checkpoints.find((cp) => !s.passed.has(cp.index)) ?? null;
  }
  private onTime = () => {
    const cp = this.nextCheckpoint();
    if (cp && this.video && this.video.currentTime >= cp.at_sec) this.reachCheckpoint(cp);
  };
  private onPlay = () => {
    if (this.state.stopped || this.seg?.awaiting != null || this.rewatchOpen) this.video?.pause();
  };
  private onSeeking = () => {
    const cp = this.nextCheckpoint();
    if (cp && this.video && this.video.currentTime > cp.at_sec + 0.25) this.video.currentTime = cp.at_sec;
  };
  private onEnded = () => {
    const cp = this.nextCheckpoint();
    if (cp) return this.reachCheckpoint(cp);
    this.markWatched();
  };
  private reachCheckpoint(cp: { index: number; at_sec: number }) {
    const s = this.seg;
    if (!s || s.awaiting === cp.index) return;
    s.awaiting = cp.index;
    const v = this.video;
    if (v) {
      v.pause();
      if (Math.abs(v.currentTime - cp.at_sec) > 0.5) v.currentTime = cp.at_sec;
    }
    this.set({ statusKey: "class.questionTime" });
    this.logLine(`Checkpoint ${cp.index + 1}`);
    this.send("checkpoint_reached", { node_id: s.node_id, index: cp.index });
  }
  private resumeAfterCheckpoint(index: number) {
    const s = this.seg;
    if (!s) return;
    s.passed.add(index);
    this.syncCheckpoints();
    if (s.awaiting !== index) return;
    s.awaiting = null;
    setTimeout(() => {
      if (this.seg !== s || s.awaiting != null || this.state.stopped) return;
      this.dismissQuestion();
      if (this.rewatchOpen) { this.resumeAfterRewatch = true; return; }
      const v = this.video;
      const atEnd = !v || v.ended || v.currentTime >= (v.duration || Infinity) - 0.3;
      if (atEnd || !s.video_url) return this.markWatched();
      this.set({ statusKey: "class.teaching" });
      v!.play().catch(() => this.toast("class.tapToPlay"));
    }, 1800);
  }
  private markWatched() {
    const s = this.seg;
    if (!s) return;
    s.done = true;
    if (!s.sent) s.sent = this.send("segment_watched", { node_id: s.node_id });
  }
  private syncCheckpoints() {
    const s = this.seg;
    this.set({ checkpoints: { total: s?.checkpoints.length ?? 0, passed: s ? s.passed.size : 0 } });
  }
  private withoutVideo(title: string, body: string) {
    this.set({ videoVisible: false });
    this.overlay({ kind: "text", title, body });
    this.markWatched();
  }
  private async playSegment(p: Payload) {
    const s: Segment = {
      node_id: p.node_id, video_url: p.video_url ?? null,
      checkpoints: [...(p.checkpoints || [])].sort((a, b) => a.at_sec - b.at_sec),
      passed: new Set(p.passed || []), awaiting: null, done: false, sent: false,
    };
    this.seg = s;
    this.syncCheckpoints();
    if (!p.video_url) return this.withoutVideo(p.title || "", p.script_text || "");
    try {
      const url = await api.mediaObjectUrl(p.video_url);
      if (this.seg !== s || this.disposed) return URL.revokeObjectURL(url);
      this.objectUrls.forEach((u) => URL.revokeObjectURL(u));
      this.objectUrls = [url];
      const v = this.video;
      if (!v) return;
      v.onerror = () => {
        if (this.seg !== s) return;
        this.withoutVideo(p.title || "", p.script_text || "");
        this.toast("class.videoFailed", "warning");
      };
      v.src = url;
      const resumeAt = Math.max(0, ...s.checkpoints.filter((cp) => s.passed.has(cp.index)).map((cp) => cp.at_sec));
      if (resumeAt > 0) v.addEventListener("loadedmetadata", () => { v.currentTime = resumeAt; }, { once: true });
      this.set({ videoVisible: true, statusKey: "class.teaching" });
      this.overlay(null);
      if (this.rewatchOpen) this.resumeAfterRewatch = true;
      else v.play().catch(() => this.toast("class.tapToPlay"));
    } catch (e) {
      if (this.seg !== s) return;
      this.withoutVideo(p.title || "", p.script_text || "");
      this.toast("class.videoFailed", "error", (e as Error).message);
    }
  }

  /* -- rewatch (pauses live, resumes exactly) ---------------------------- */
  beginRewatch() {
    this.rewatchOpen = true;
    this.resumeAfterRewatch = !!this.video && !this.video.paused;
    this.video?.pause();
  }
  endRewatch() {
    this.rewatchOpen = false;
    if (this.resumeAfterRewatch && !this.state.stopped && this.seg?.awaiting == null && this.state.videoVisible) {
      this.video?.play().catch(() => {});
    }
    this.resumeAfterRewatch = false;
  }

  /* -- answers ---------------------------------------------------------- */
  submit(answer: string) {
    const q = this.state.question;
    if (!q || this.state.grading) return;
    if (!answer.trim()) return this.toast("class.emptyAnswer", "warning");
    const sent = this.send("student_response", {
      node_id: q.node_id, interaction_id: q.interaction_id, raw_answer: answer,
      response_time_sec: (Date.now() - this.questionShownAt) / 1000,
    });
    if (!sent) return this.toast("class.answerKept", "warning");
    this.set({
      grading: true, statusKey: "class.grading",
      qa: this.state.qa.map((e) => (e.question.interaction_id === q.interaction_id ? { ...e, answer } : e)),
    });
  }
  private dismissQuestion() { this.set({ question: null, feedback: null, feedbackFor: null, grading: false }); }

  /* -- paused lesson actions ------------------------------------------- */
  async act(kind: "continue" | "skip" | "relearn", nodeId?: string) {
    if (kind === "continue") await api.continueLesson(this.lessonId);
    else if (kind === "skip") await api.skipConcept(this.lessonId);
    else await api.relearnConcept(this.lessonId, nodeId!);
  }

  /* -- socket ----------------------------------------------------------- */
  private send(type: string, payload: Payload) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ event_type: type, payload }));
      return true;
    }
    return false;
  }
  private onOnline = () => {
    if (!this.socket && this.reconnectTimer && !this.closedByUs) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
      this.connect();
    }
  };
  private scheduleReconnect() {
    if (this.closedByUs || this.reconnectTimer) return;
    this.reconnectAttempts += 1;
    if (this.reconnectAttempts > MAX_RECONNECT) {
      this.set({ connection: "offline" });
      return this.overlay({ kind: "offline" });
    }
    const delay = Math.min(15000, 1000 * 2 ** (this.reconnectAttempts - 1));
    this.set({ connection: "reconnecting" });
    this.logLine(`Reconnecting in ${Math.round(delay / 1000)}s`);
    this.reconnectTimer = setTimeout(() => { this.reconnectTimer = null; this.connect(); }, delay);
  }
  private async connect() {
    if (this.disposed) return;
    this.set({ connection: this.reconnectAttempts ? "reconnecting" : "connecting" });
    try {
      const { ticket, ws_path } = await api.getWsTicket(this.lessonId);
      if (this.disposed) return;
      const socket = new WebSocket(wsUrl(ws_path, ticket));
      this.socket = socket;
      socket.onopen = () => {
        if (this.reconnectAttempts) this.toast("class.reconnected", "success");
        this.reconnectAttempts = 0;
        this.set({ connection: "live" });
        this.logLine("Connected");
      };
      socket.onmessage = (ev) => {
        let m: { event_type?: string; payload?: Payload; error?: string };
        try { m = JSON.parse(ev.data); } catch { return; }
        if (m.error) {
          this.lastError = m.error;
          this.toast("common.error", "error", m.error);
          this.logLine(`Error: ${m.error}`);
          return;
        }
        const h = (this.handlers as Record<string, (p: Payload) => void>)[m.event_type || ""];
        h?.(m.payload || {});
      };
      socket.onclose = (ev) => {
        if (this.socket !== socket || this.closedByUs) return;
        this.socket = null;
        if (ev.code === CLOSE_SUPERSEDED) {
          this.closedByUs = true;
          this.set({ connection: "elsewhere" });
          return this.overlay({ kind: "elsewhere" });
        }
        if (ev.code === CLOSE_POLICY) {
          this.set({ connection: "unavailable" });
          return this.overlay({ kind: "error", titleKey: "class.couldNotStart", body: this.lastError || "" });
        }
        this.scheduleReconnect();
      };
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      if (status >= 400 && status < 500) {
        this.set({ connection: "unavailable" });
        return this.overlay({ kind: "error", titleKey: "class.couldNotStart", body: (e as Error).message });
      }
      this.scheduleReconnect();
    }
  }

  private setAdaptation(action: "MODIFY" | "REGENERATE" | "HUMAN" | null, key?: string) {
    if (!action) {
      this.lastAdaptationKey = null;
      if (this.adaptationTimer) clearTimeout(this.adaptationTimer);
      return this.set({ adaptation: null });
    }
    if (this.lastAdaptationKey === key) return;
    this.lastAdaptationKey = key ?? null;
    this.set({ adaptation: { action, slow: false } });
    if (this.adaptationTimer) clearTimeout(this.adaptationTimer);
    if (action !== "HUMAN") {
      this.adaptationTimer = setTimeout(() => {
        if (this.lastAdaptationKey === key && this.state.adaptation) this.set({ adaptation: { ...this.state.adaptation, slow: true } });
      }, 20000);
    }
  }

  private paused(concept: string) {
    this.closedByUs = true;
    this.video?.pause();
    this.set({ stopped: true, connection: "paused", statusKey: "class.paused", question: null });
    this.overlay({ kind: "paused", concept });
  }

  private handlers = {
    session_ready: (p: Payload) => {
      this.set({ title: p.title || this.state.title });
      this.logLine(p.resumed ? "Resumed" : "Lesson started");
      if (p.resumed) {
        api.lessonNotes(this.lessonId).then((r) => this.set({
          collected: r.notes.map((n: SavedNote) => ({
            node_id: n.node_id, concept: n.concept,
            points: n.key_points?.length ? n.key_points : sentenceFallback(n.script_text).slice(0, 3),
            example: n.example || undefined,
          })),
        })).catch(() => {});
      }
    },
    curriculum_loaded: (p: Payload) => {
      const known = new Map(this.state.nodes.map((n) => [n.node_id, n]));
      this.set({
        nodes: (p.nodes || []).map((n: Payload) => ({
          status: "pending", attempts: 0, video_url: null, ...(known.get(n.node_id) || {}), ...n,
          ...(known.has(n.node_id) ? { status: known.get(n.node_id)!.status } : {}),
        })),
      });
    },
    lesson_plan_update: (p: Payload) => {
      this.set({ nodes: (p.nodes || []).map((n: Payload) => ({ video_url: null, ...n, status: "pending", attempts: 0 })) });
      this.toast("class.planRebuilt", "info");
    },
    progress_snapshot: (p: Payload) => {
      this.set({
        nodes: (p.nodes || []).map((n: Payload) => ({ video_url: null, attempts: 0, ...n })),
        progress: { pct: p.progress_pct ?? 0, done: p.nodes_completed ?? 0, total: p.node_count ?? 0 },
      });
    },
    ai_state: (p: Payload) => {
      const keys: Record<string, MessageKey> = {
        PLAN: "class.connecting", TEACH: "class.teaching", INTERACT: "class.questionTime",
        EVALUATE: "class.grading", ASSESS: "class.assessing", RESUME: "class.resume",
      };
      this.set({ statusKey: keys[p.state] ?? null, ...(p.node_id ? { currentNodeId: p.node_id } : {}) });
      if (p.state === "TEACH") this.overlay({ kind: "loading", title: p.concept || "", bodyKey: "class.writing" });
    },
    explanation_chunk: (p: Payload) => {
      const points = (p.notes?.key_points || []).filter(Boolean);
      const visual = p.visual_spec || {};
      const notes: NotesView = {
        node_id: p.node_id, concept: p.concept || p.title || "", depth: p.depth, est_minutes: p.est_minutes,
        formula: visual.type === "equation" && typeof visual.content === "string" ? plainMath(visual.content) : undefined,
        points: points.length ? points : sentenceFallback(p.script_text), example: p.notes?.example || undefined,
        transcript: p.script_text || "",
      };
      const entry = { node_id: p.node_id, concept: notes.concept, points: points.length ? points : sentenceFallback(p.script_text).slice(0, 3), example: notes.example };
      const at = this.state.collected.findIndex((c) => c.node_id === entry.node_id);
      const collected = at >= 0 ? this.state.collected.map((c, i) => (i === at ? entry : c)) : [...this.state.collected, entry];
      this.set({ currentNodeId: p.node_id, notes, collected });
      if (p.replay && this.seg?.node_id === p.node_id) return;
      this.dismissQuestion();
      this.setAdaptation(null);
      this.overlay({ kind: "loading", title: notes.concept, bodyKey: p.replay ? "class.loadingConcept" : "class.rendering" });
    },
    render_started: () => {
      const o = this.state.overlay;
      this.overlay({ kind: "loading", title: o && "title" in o ? (o as { title: string }).title : "", bodyKey: "class.rendering" });
    },
    video_segment: (p: Payload) => {
      const cur = this.seg;
      if (cur && cur.node_id === p.node_id && cur.video_url === p.video_url) {
        (p.passed || []).forEach((i: number) => cur.passed.add(i));
        this.syncCheckpoints();
        if (cur.awaiting != null && !this.state.question) this.send("checkpoint_reached", { node_id: cur.node_id, index: cur.awaiting });
        else if (cur.done) { cur.sent = false; this.markWatched(); }
        return;
      }
      void this.playSegment(p);
    },
    render_failed: (p: Payload) => {
      this.toast("class.videoFailed", "error");
      this.seg = { node_id: p.node_id, video_url: null, checkpoints: [], passed: new Set(), awaiting: null, done: false, sent: false };
      this.withoutVideo(this.state.notes?.concept || "", this.state.notes?.transcript || p.reason || "");
    },
    answer_rejected: (p: Payload) => {
      this.toast("class.emptyAnswer", "warning", p.reason);
      this.set({ grading: false });
    },
    citation_updated: (p: Payload) => {
      this.set({ citation: p.excerpt ? (p as CitationView) : { none: true } });
    },
    interaction_event: (p: Payload) => {
      const q = p as InteractionEvent;
      if (q.interaction_id && this.state.question?.interaction_id === q.interaction_id) {
        // Re-asked after a reconnect: keep the card and what was typed; allow a resubmit.
        return this.set({ grading: false });
      }
      const s = this.seg;
      if (s && q.node_id === s.node_id && q.checkpoint_index != null) {
        const cp = s.checkpoints.find((c) => c.index === q.checkpoint_index);
        s.awaiting = q.checkpoint_index;
        const v = this.video;
        if (v) {
          v.pause();
          if (cp && this.state.videoVisible && Math.abs(v.currentTime - cp.at_sec) > 0.5) v.currentTime = cp.at_sec;
        }
      }
      this.questionShownAt = Date.now();
      const qa = this.state.qa.some((e) => e.question.interaction_id === q.interaction_id) ? this.state.qa : [...this.state.qa, { question: q }];
      this.set({ question: q, feedback: null, feedbackFor: null, grading: false, statusKey: "class.questionTime", qa });
    },
    resume_video: (p: Payload) => {
      if (this.seg?.node_id === p.node_id && p.index != null) this.resumeAfterCheckpoint(p.index);
    },
    evaluation_result: (p: Payload) => {
      const r = p as EvaluationEvent;
      const id = r.interaction_id || this.state.question?.interaction_id || null;
      this.set({
        grading: false, feedback: r, feedbackFor: id,
        qa: this.state.qa.map((e) => (e.question.interaction_id === id ? { ...e, result: r } : e)),
      });
    },
    adaptation_decision: (p: Payload) => {
      this.logLine(`Adaptation: ${p.action}`);
      if (p.action === "ALLOW") return this.setAdaptation(null);
      if (p.action === "MODIFY" || p.action === "REGENERATE" || p.action === "HUMAN") {
        this.setAdaptation(p.action, `${p.target_node_id || this.state.currentNodeId}:${p.action}`);
      }
    },
    assessment_report: (p: Payload) => {
      this.closedByUs = true;
      this.set({ connection: "done" });
      this.overlay({ kind: "complete", score: p.score_pct ?? 0 });
      setTimeout(() => this.onNavigate(`/report/${this.lessonId}`), 2200);
    },
    human_escalation: (p: Payload) => {
      this.setAdaptation("HUMAN", `${this.state.currentNodeId}:HUMAN`);
      this.paused(p.escalation?.concept || this.state.notes?.concept || "");
    },
    review_needed: (p: Payload) => {
      this.closedByUs = true;
      this.video?.pause();
      this.set({ stopped: true, connection: "paused", question: null });
      this.overlay({ kind: "review", concepts: p.concepts || [] });
    },
    lesson_paused: (p: Payload) => this.paused(p.escalation?.concept || ""),
    pong: () => {},
  };
}
