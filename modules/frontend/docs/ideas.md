# Shikshak AI — Frontend Architecture & Creative Ideas

## Product Philosophy: The "Quiet Signal"
Shikshak AI is built on the philosophy of a calm, attentive digital tutor. Unlike overwhelming dashboards or flashing game-like gamification, Shikshak AI prioritizes clarity, cognitive ease, and radical pedagogical transparency.

### Core Pillars
1. **Explain the Reasoning, Not Just the Answer**: At every stage of the session, the learner sees *why* an adaptation is happening (e.g. "Misconception detected: confused cell wall with membrane → switching to selective doorway analogy").
2. **Pedagogical Feedback Loops**: Every checkpoint question is not a test, but a probe to detect understanding or misconceptions. The system adapts before moving to the next concept.
3. **Multilingual Inclusivity**: Real-time language switching across English, Hindi, and Hinglish with culturally rooted analogies.

## Creative Feature Roadmap & Hackathon Highlights
- **Dynamic Whiteboard Canvas**: In addition to video playback, the center stage renders progressive mathematical equations (KaTeX) and diagram flowcharts synchronized with speech timestamps.
- **Audio-Visual Teacher Visemes**: 24 FPS mouth movement aligned with audio phonemes for zero-GPU lightweight animation.
- **AI Inspector**: A live telemetry HUD showing the underlying state machine (`PLAN -> TEACH -> INTERACT -> EVALUATE -> ADAPT`), confidence score meters, and grounding document citations.
- **Interactive Notes & Takeaway Synthesis**: Automatic extraction of student takeaways and flashcard exports.
