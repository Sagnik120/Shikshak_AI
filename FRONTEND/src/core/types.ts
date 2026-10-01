/** Shapes returned by the FastAPI backend. Shared by web and (later) mobile. */

export type Level = "beginner" | "intermediate" | "advanced";

export interface User {
  id: string;
  email: string;
  full_name: string;
  initials: string;
  role: "student" | "admin" | string;
  is_verified: boolean;
  preferred_language: string;
  preferred_level: Level | string;
  preferred_style?: string | null;
  default_time_budget_min: number;
  grade?: string | null;
  board?: string | null;
  avatar_color: string;
  avatar_url?: string | null;
  avatar_choice?: string | null;
  mentor_name?: string | null;
  mentor_email?: string | null;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export type LessonStatus = "created" | "planned" | "in_progress" | "completed" | "escalated" | "abandoned";

export interface Escalation {
  id: string;
  lesson_id: string;
  node_id: string;
  concept: string;
  status: "open" | "continued" | "resolved" | "skipped" | "closed";
  reason?: string | null;
  resolution?: string | null;
  mentor_notified: boolean;
  opened_at: string;
  continued_at?: string | null;
  closed_at?: string | null;
}

export interface Lesson {
  id: string;
  title: string;
  source: "topic" | "document";
  topic?: string | null;
  status: LessonStatus;
  level: Level;
  language: string;
  node_count: number;
  nodes_completed: number;
  progress_pct: number;
  score_pct: number | null;
  watch_minutes: number;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  escalation: Escalation | null;
  needs_review: Array<{ node_id: string; concept: string }>;
  relearning?: string | null;
  review_pending: boolean;
  to_review: number;
}

export interface QA {
  id: string;
  question_text: string;
  question_type: string;
  options: string[];
  expected_concept: string | null;
  raw_answer: string | null;
  correct: boolean | null;
  partial_credit: number;
  feedback_text: string | null;
  misconception_tag?: string | null;
  adaptation_action?: string | null;
  asked_at: string;
}

export interface Citation {
  source_title?: string;
  excerpt?: string;
  section_title?: string | null;
  page_or_slide?: number | null;
  chunk_count?: number;
  risk_level?: string;
}

export interface LessonNode {
  node_id: string;
  position: number;
  concept: string;
  depth: string;
  est_minutes: number;
  status: string;
  attempts: number;
  mastery_score: number;
  times_reexplained: number;
  script_text: string | null;
  notes: { key_points?: string[]; example?: string | null } | null;
  video_url: string | null;
  captions_url: string | null;
  duration_sec: number;
  citation: Citation | null;
  review_note: string | null;
  checkpoints: Array<{ index: number; at_sec: number }>;
  interactions: QA[];
}

export interface LessonDetail extends Lesson {
  nodes: LessonNode[];
  report: {
    score_pct: number;
    strong_areas: string[];
    weak_areas: string[];
    recommended_next: string[];
    narrative_feedback: string;
    created_at: string;
  } | null;
  escalations: Escalation[];
  constraints: { level: string; language: string; time_budget_min: number; style?: string | null };
}

export interface LessonList {
  lessons: Lesson[];
  count: number;
  total: number;
  offset: number;
  has_more: boolean;
}

export interface Dashboard {
  learner: { full_name: string; initials: string; avatar_color: string; member_since: string };
  stats: {
    lessons_started: number;
    lessons_completed: number;
    lessons_in_progress: number;
    lessons_paused?: number;
    average_score_pct: number;
    accuracy_pct: number;
    total_questions: number;
    correct_questions: number;
    learning_minutes: number;
    streak_days: number;
    longest_streak: number;
    concepts_mastered: number;
    concepts_to_review: number;
  };
  strong_concepts: string[];
  weak_concepts: string[];
  resume_lesson: Lesson | null;
  needs_attention: Array<{
    kind: "paused" | "review";
    lesson_id: string;
    lesson_title: string;
    concept: string;
    node_id?: string;
    since?: string;
  }>;
  recent_lessons: Lesson[];
  score_trend: Array<{ lesson_id: string; score_pct: number; date: string }>;
  activity_calendar: Array<{ date: string; count: number }>;
}

export interface Analytics {
  accuracy_trend: Array<{ date: string; accuracy_pct: number; questions: number }>;
  concept_strength: Array<{ concept: string; mastery_pct: number; attempts: number; reexplains: number }>;
  weakest: Array<{ concept: string; mastery_pct: number }>;
  strongest: Array<{ concept: string; mastery_pct: number }>;
  misconceptions: Array<{ tag: string; count: number }>;
  time_on_task: Array<{ date: string; minutes: number }>;
  response_time: { average_sec: number; samples: number };
  totals: { lessons: number; completed: number; questions: number; correct: number; learning_minutes: number };
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  size_bytes: number;
  status: string;
  chunk_count: number;
  chapters: string[];
  key_terms: string[];
  created_at?: string;
}

export interface PracticeQuestion {
  interaction_id: string;
  node_id: string;
  concept: string;
  question_text: string;
  type: string;
  options: string[];
  your_lesson_answer: string | null;
  lesson_correct: boolean;
  needs_practice: boolean;
  last_practice: { correct: boolean; answer: string; answered_at: string } | null;
}
export interface PracticeSet { lesson_id: string; title: string; questions: PracticeQuestion[] }
export interface PracticeResult { correct: boolean; feedback_text: string; model_answer: string }

export interface SavedNote {
  node_id: string; concept: string; depth?: string; est_minutes?: number; status?: string;
  key_points: string[]; example?: string | null; script_text?: string | null; citation?: Citation | null;
}

/* -- live classroom protocol (WebSocket) ----------------------------------- */

export interface Checkpoint { index: number; at_sec: number }

export interface VideoSegment {
  node_id: string;
  title: string;
  script_text: string;
  video_url: string | null;
  captions_url?: string | null;
  duration_sec: number;
  checkpoints?: Checkpoint[];
  passed?: number[];
  replay?: boolean;
}

export interface InteractionEvent {
  interaction_id: string;
  node_id: string;
  checkpoint_index?: number;
  question_text: string;
  type: string;
  options: string[];
}

export interface EvaluationEvent {
  interaction_id?: string;
  node_id: string;
  correct: boolean;
  partial_credit: number;
  feedback_text: string;
  misconception_tag?: string | null;
}

export interface ProgressNode {
  node_id: string;
  concept: string;
  status: string;
  mastery_score: number;
  attempts: number;
  checkpoint_question: boolean;
  video_url: string | null;
}

/* -- admin ----------------------------------------------------------------- */

export interface AdminOverview {
  learners: number;
  active_today: number;
  lessons: number;
  completed: number;
  live_now: number;
  open_escalations: number;
  questions_answered: number;
  accuracy_pct: number;
  avg_score_pct: number;
  escalations_total: number;
  funnel: { concepts_checked: number; first_time: number; rescued: number; still_stuck: number; needed_human: number };
  daily: Array<{ date: string; lessons: number; questions: number; learners: number; right: number; wrong: number; rescued: number; escalations: number; completed: number; started: number }>;
}
export interface AdminLive {
  sessions: Array<{
    lesson_id: string; title: string; learner: string; concept: string | null;
    fsm_state: string; progress_pct: number; connected_for_sec: number;
  }>;
}
export interface AdminEscalations {
  escalations: Array<Escalation & {
    learner: string; learner_email: string; lesson_title: string;
    last_question?: string | null; last_answer?: string | null; wrong_answers: number;
    minutes_open: number;
  }>;
  counts: Record<string, number>;
}
export interface AdminInsights {
  hardest_concepts: Array<{ concept: string; attempts: number; accuracy_pct: number; learners: number }>;
  missed_questions: Array<{ question: string; concept: string; asked: number; wrong_pct: number }>;
  misconceptions: Array<{ tag: string; count: number }>;
  attempts_to_mastery: number;
  adaptation_mix: Record<string, number>;
}
export interface AdminQuality {
  grounding: Record<string, number>;
  llm: { live: boolean; model: string; cooldown_active: boolean; cooldown_remaining_sec: number };
  script_words_vs_target: number | null;
  explanations: number;
  questions_by_type: Record<string, number>;
}
export interface AdminPipeline {
  renders: { total: number; avg_video_sec: number; failed: number };
  memory_mb: number | null;
  uptime_sec: number;
  events_last_hour: Record<string, number>;
  reconnects_today: number;
}
export interface AdminLearners {
  learners: Array<{
    id: string; full_name: string; email: string; avatar_color: string; avatar_url?: string | null;
    lessons: number; completed: number; accuracy_pct: number; last_active: string | null; open_escalations: number;
  }>;
}
export interface AdminLearnerDetail {
  learner: AdminLearners["learners"][number] & { grade?: string | null; created_at: string };
  lessons: Lesson[];
  strong_concepts: string[];
  weak_concepts: string[];
  escalations: Escalation[];
  practice_attempts: number;
}

/* -- learner journey ---------------------------------------------------- */

export interface JourneyDay { date: string; answers: number; correct: number; videos: number; practice: number; started: number; completed: number; minutes: number }
export interface Badge { id: string; group: string; tier: number; threshold: number; value: number; earned: boolean; earned_at: string | null }
export interface Journey {
  today: string;
  days: JourneyDay[];
  streak: { current: number; longest: number; active_days: number; last_active: string | null };
  level: { xp: number; level: number; floor: number; next: number; title: string };
  totals: { answers: number; correct: number; lessons_started: number; lessons_completed: number; concepts_mastered: number; practice: number; minutes: number; videos: number; documents: number; best_right_in_a_row: number };
  understanding: { concepts_checked: number; first_try: number; rescued: number; still_stuck: number };
  mastery: { mastered: number; watched: number; learning: number; to_review: number; not_started: number };
  concepts: Array<{ concept: string; mastery_pct: number; attempts: number; reexplains: number; status: string }>;
  weekday: number[];
  hours: number[];
  badges: Badge[];
  months: Array<{ month: string; active_days: number; earned: boolean; needed: number }>;
}
