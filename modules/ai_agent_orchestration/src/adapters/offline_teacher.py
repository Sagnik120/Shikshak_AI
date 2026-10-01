"""Deterministic, context-aware stand-in for the LLM.

Serves the whole lesson when no Gemini key is configured, and — more often in
production — whenever a live call fails (free-tier 429s, timeouts). It used to
return one canned lesson for every request: an inertia script, a
thermodynamics quiz and a 95% "outstanding progress" report, whatever the
learner asked about. Here every reply is built from the request itself:

* planner    -> nodes from the document's chapters, or from the topic
* explainer  -> script from the retrieved document passages for the node
* questioner -> a question about the concept that was just taught
* judge      -> credit from overlap with the expected concept
* assessment -> numbers and wording from the actual evaluation history

It never invents facts: without a document it teaches only the framing of the
concept, and says so plainly rather than making content up.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List

_WORD_RE = re.compile(r"[^\W\d_][\w'-]*", re.UNICODE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")
_CHAPTER_PREFIX = re.compile(
    r"^\s*(chapter|unit|section|part|lesson|module)\s*[\w.]*\s*[:.\-–—]\s*", re.IGNORECASE
)
_FORMULA_RE = re.compile(r"\b([A-Za-z]{1,3}\s*=\s*[A-Za-z0-9][A-Za-z0-9 ×·*/^+\-]{0,20})")
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "what", "how", "why",
    "are", "was", "were", "its", "their", "about", "your", "you", "our", "has", "have",
    "not", "but", "can", "will", "which", "when", "where", "who", "all", "any", "one",
    "each", "per", "than", "then", "them", "they", "also", "more", "most", "some",
}


def _payload(text: str) -> dict:
    """Agents send "<instruction>:\\n{json}" — recover the JSON part."""
    start = text.find("{")
    if start < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}


def _speech_safe(text: str) -> str:
    """Script text is spoken: no markdown, LaTeX or stray symbols."""
    text = re.sub(r"\$+|\\[a-zA-Z]+|[{}#*_`|<>\[\]]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentences(passages: List[str]) -> List[str]:
    out: List[str] = []
    for passage in passages:
        for s in _SENTENCE_SPLIT.split(_speech_safe(str(passage))):
            s = s.strip()
            # Drop headings and fragments; keep sentences worth speaking.
            if len(s.split()) >= 5 and s[-1:] in ".!?।":
                out.append(s)
    seen, unique = set(), []
    for s in out:
        if s.lower() not in seen:
            seen.add(s.lower())
            unique.append(s)
    return unique


def _terms(text: str) -> set:
    return {
        w.lower().rstrip("s")
        for w in _WORD_RE.findall(text or "")
        if len(w) > 2 and w.lower() not in _STOPWORDS
    }


def _clean_concept(text: str) -> str:
    text = _CHAPTER_PREFIX.sub("", str(text)).strip(" :-–—")
    return text[:90] or "Key idea"


def _relevant(sentences: List[str], concept: str) -> List[str]:
    """Order sentences by how much they talk about this concept."""
    want = _terms(concept)
    scored = sorted(
        enumerate(sentences),
        key=lambda pair: (-len(want & _terms(pair[1])), pair[0]),
    )
    return [s for _, s in scored]


class OfflineTeacher:
    """Builds contract-valid agent replies from the request context alone."""

    def reply(self, system: str, user: str) -> str:
        sys_lower = system.lower()
        full_lower = (system + " " + user).lower()
        data = _payload(user)

        if (
            "evaluating student understanding" in sys_lower
            or "interactive question" in sys_lower
            or "interactionevent" in full_lower
        ):
            return json.dumps(self.question(data))
        if "assessment evaluator" in sys_lower or "assessmentreport" in full_lower or "score_pct" in sys_lower:
            return json.dumps(self.assessment(data))
        if (
            "explaining a specific lesson concept" in sys_lower
            or "teachingsegment" in full_lower
            or ("teaching segment" in sys_lower and "question" not in sys_lower)
        ):
            return json.dumps(self.segment(data))
        if (
            "planner" in sys_lower
            or "lessonplan" in full_lower
            or "lesson plan" in sys_lower
            or "curriculum" in full_lower
        ):
            if not data:
                hint = re.search(r"topic\s*:\s*([^\n.]{2,80})", user, re.IGNORECASE)
                data = {"_topic_hint": hint.group(1).strip()} if hint else {}
            return json.dumps(self.plan(data))
        if "misconception" in full_lower:
            # A taxonomy tag is a diagnosis; offline there is no basis for one.
            return json.dumps({"misconception_tag": None})
        if "student answer:" in full_lower:
            return json.dumps(self.judge(user))
        return json.dumps({"status": "ok", "message": "offline"})

    # -- planner ----------------------------------------------------------

    def plan(self, data: dict) -> dict:
        constraints = dict(data.get("constraints") or {})
        constraints.setdefault("level", "beginner")
        constraints.setdefault("language", "en")
        budget = constraints.get("time_budget_min")
        minutes = budget if isinstance(budget, int) and budget > 0 else 15
        if budget != "multi_day_plan":
            constraints["time_budget_min"] = minutes

        document = data.get("document") or {}
        topic = str(data.get("topic") or data.get("_topic_hint") or "").strip()
        if not topic and document.get("filename"):
            topic = re.sub(r"[_\-]+", " ", str(document["filename"]).rsplit(".", 1)[0]).strip()
        topic = topic or "Today's topic"

        concepts = [_clean_concept(c) for c in (document.get("chapters") or []) if str(c).strip()]
        concepts = list(dict.fromkeys(concepts))
        count = max(2, min(4, minutes // 3))
        if not concepts:
            concepts = [
                f"What is {topic}?",
                f"How {topic} works",
                f"{topic} in everyday life",
                f"Putting {topic} together",
            ]
        concepts = concepts[:count]

        # Split the budget so the plan actually fills the time asked for.
        base, extra = divmod(minutes, len(concepts))
        depths = ["intro"] + ["core"] * (len(concepts) - 2) + ["advanced"] if len(concepts) > 2 else ["intro", "core"]
        excerpts = " ".join(document.get("excerpts") or [])
        nodes = []
        for i, concept in enumerate(concepts):
            has_formula = bool(_FORMULA_RE.search(concept)) or ("=" in excerpts and "law" in concept.lower())
            nodes.append(
                {
                    "node_id": f"node_{i + 1}",
                    "concept": concept,
                    "depth": depths[min(i, len(depths) - 1)],
                    "est_minutes": max(1, base + (1 if i < extra else 0)),
                    "visual_type": "equation" if has_formula else "diagram",
                    "checkpoint_question": True,
                }
            )
        return {
            "lesson_id": "lesson_offline",
            "source": "document" if document else "topic",
            "constraints": constraints,
            "nodes": nodes,
        }

    # -- explainer --------------------------------------------------------

    def segment(self, data: dict) -> dict:
        node = data.get("node") or {}
        concept = str(node.get("concept") or "this idea")
        language = (data.get("constraints") or {}).get("language") or "en"
        target = int((data.get("script_length") or {}).get("target_words") or 150)
        grounding = _relevant(_sentences(data.get("grounding_context") or []), concept)
        retry = bool(data.get("previous_feedback"))

        opening = (
            f"Let's look at {concept} again, from a different angle this time."
            if retry
            else f"In this part we are going to learn about {concept}."
        )
        body: List[str] = []
        if grounding:
            words = 0
            ordered = list(reversed(grounding)) if retry else grounding
            for s in ordered:
                body.append(s)
                words += len(s.split())
                if words >= target * 0.8:
                    break
            bridge = "Here is what your study material says."
        else:
            bridge = (
                f"Think of {concept} as one building block of the bigger picture. "
                "First, notice what the idea is about. Then ask what changes, and what stays the same. "
                "Finally, try to connect it to something you have seen in daily life."
            )
        recap = f"To recap: keep the main idea of {concept} in mind, because the next question checks it."
        script = " ".join([opening, bridge, *body, recap])

        key_points = [s for s in grounding[:4]] or [
            f"{concept} is the focus of this section.",
            "Identify what the idea describes and when it applies.",
            "Connect it to an everyday example.",
        ]
        formula = next((m.group(1).strip() for s in grounding for m in [_FORMULA_RE.search(s)] if m), None)
        if node.get("visual_type") == "equation" and formula:
            visual = {"type": "equation", "content": formula}
        else:
            visual = {
                "type": "diagram",
                "content": {"title": concept, "nodes": [p[:60] for p in key_points[:4]]},
            }
        example = next((s for s in grounding if re.search(r"example|for instance|such as|when you", s, re.I)), None)
        return {
            "node_id": node.get("node_id") or "node",
            "script_text": script,
            "language": language,
            "visual_spec": visual,
            "avatar_cue": "emphasis" if retry else "neutral",
            "notes": {"key_points": key_points[:5], "example": example},
        }

    # -- questioner -------------------------------------------------------

    def question(self, data: dict) -> dict:
        node = data.get("node") or {}
        concept = str(node.get("concept") or "this idea")
        segment = data.get("recent_teaching_segment") or {}
        notes = segment.get("notes") or {}
        points = [p for p in (notes.get("key_points") or []) if isinstance(p, str)]
        # Ask the learner to recall the section in their own words; graded by
        # overlap with what was actually taught, never against a made-up key.
        expected = " ".join(points[:2]) or concept
        return {
            "node_id": node.get("node_id") or "node",
            "question_text": f"In your own words, what is the main idea of \"{concept}\"?",
            "type": "short_answer",
            "options": [],
            "expected_concept": expected[:400],
        }

    # -- free-text judge ---------------------------------------------------

    def judge(self, user: str) -> dict:
        def field(name: str) -> str:
            m = re.search(rf"{name}:\s*(.*)", user, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        answer = _terms(field("Student answer"))
        source = field("Source material")
        target = _terms(field("Expected concept") + " " + source)
        if not answer or not target:
            credit = 0.0
        else:
            # Recall of the key terms, saturating: 4 relevant terms is a full answer.
            credit = min(1.0, len(answer & target) / min(4, len(target)))
        if (not source or source.lower() == "none provided") and len(answer) >= 4:
            # Topic-only and offline: there is nothing authoritative to grade a
            # real explanation against, so a genuine attempt is not failed.
            credit = max(credit, 0.7)
        credit = round(credit, 2)
        correct = credit >= 0.5
        feedback = (
            "Good — your answer covers the key idea."
            if correct
            else "Not quite yet — your answer misses the key idea of this section."
        )
        return {"correct": correct, "partial_credit": credit, "confidence": 0.6, "feedback_text": feedback}

    # -- assessment -------------------------------------------------------

    def assessment(self, data: dict) -> dict:
        history = [h for h in (data.get("session_history") or []) if isinstance(h, dict)]
        best: Dict[str, float] = {}
        for h in history:
            credit = 1.0 if h.get("correct") else float(h.get("partial_credit") or 0.0)
            node = str(h.get("node_id") or "")
            best[node] = max(best.get(node, 0.0), credit)
        score = round(100.0 * sum(best.values()) / len(best), 1) if best else 0.0
        weak = [n for n, v in best.items() if v < 0.7]
        if not best:
            narrative = "This lesson had no checkpoint answers yet, so there is nothing to score."
        elif score >= 80:
            narrative = f"Great work — you scored {score:.0f}% and showed a solid grasp of the lesson."
        elif score >= 50:
            narrative = f"Good effort — you scored {score:.0f}%. Revisit the weaker sections once more."
        else:
            narrative = f"You scored {score:.0f}%. Rewatch the sections you found hard, then try again."
        return {
            "lesson_id": str(data.get("lesson_id") or "lesson_offline"),
            "score_pct": score,
            # History only carries node ids; the backend fills these from the
            # measured per-node mastery, with the real concept names.
            "strong_areas": [],
            "weak_areas": [],
            "recommended_next": ["Review the weak sections, then retake this lesson"] if weak else [],
            "narrative_feedback": narrative,
        }


_teacher = OfflineTeacher()


def offline_reply(messages: List[Dict[str, str]]) -> str:
    system = " ".join(m.get("content", "") for m in messages if m.get("role") == "system")
    user = " ".join(m.get("content", "") for m in messages if m.get("role") != "system")
    return _teacher.reply(system, user)
