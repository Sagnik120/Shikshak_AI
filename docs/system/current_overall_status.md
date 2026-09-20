# Shikshak AI — Current Overall Status

## 1. Current System State
The Shikshak AI application is currently in an advanced state of integration. The major cross-module integration path has been substantially connected and proven functionally viable. Core orchestration, external API connectivity, visual generation, and assessment all work together in the intended sequential pipeline. The primary focus is now stabilizing the frontend UI components and ensuring state persists correctly across websocket events during edge cases.

## 2. Module Validation Status
| Module | Isolated Testing | Current Status |
|---|---|---|
| AI Agent Orchestration | Completed | Functional |
| RAG | Completed | Functional |
| ML Core | Completed | Functional |
| Avatar & Voice | Completed | Functional |
| Frontend/Backend Integration | Initial E2E tested | Substantially connected, requires stabilization |

## 3. Verified End-to-End Flow
The following flow was verified to functionally execute end-to-end:
Topic → RAG → Gemini/LLM → Plan → Explanation → Question → Answer → Evaluation → Adaptation → Avatar/Voice

*(Note: LLM capability was verified manually by the human during the previous overall web test, not programmatically by this analysis).*

## 4. Current Known Issues
1. **Static Frontend Details:** Several components (e.g., citation source text, initial explanation chunk) use hardcoded placeholder text in the HTML, which temporarily displays before websocket events overwrite them.
2. **Video Controls:** The generated classroom video cannot be paused, forwarded, or reversed. The `<video>` element lacks the `controls` attribute and the custom UI overlay is not fully wired.
3. **Free-Form Answer Input:** The frontend `checkpoint-card` component currently only implements radio buttons for `mcq`. If a free-form question (e.g., `short_answer`) is generated, there is no UI component to enter text.
4. **Incorrect Adaptation Integration:** After a student encounters `MODIFY` followed by another failure, the Orchestrator incorrectly evaluates the state as `MODIFY` again instead of progressing to `HUMAN`.

## 5. Root-Cause Analysis

### Issue 1: Static Frontend Details
- **Affected Component:** `classroom.html`, `classroom.js`
- **Evidence:** Source inspection shows hardcoded strings like `"Biology_Notes.pdf — Page 12"` inside `citation-source-text`.
- **Cause:** Leftover UI placeholders from early prototyping.
- **Proposed Solution:** Remove hardcoded text. Introduce simple CSS loading/empty states until the websocket populates them.

### Issue 2: Video Controls
- **Affected Component:** `classroom.html`
- **Evidence:** `<video id="lesson-video">` does not possess a native `controls` attribute. The HTML includes a custom `.video-controls-bar` but its JS wiring in `classroom.js` is incomplete.
- **Cause:** Custom video UI was partially implemented.
- **Proposed Solution:** Add `controls` attribute directly to the `<video>` element for robust native playback, and remove/hide the incomplete custom `.video-controls-bar`.

### Issue 3: Free-Form Answer Input
- **Affected Component:** `classroom.html`, `classroom.js`
- **Evidence:** `InteractionEvent` schema supports `mcq`, `short_answer`, `problem`, etc. However, `classroom.js` blindly maps `event.options` to radio buttons and does not check `event.type`.
- **Cause:** UI component for text inputs was never built.
- **Proposed Solution:** Add a `<textarea id="free-form-answer">` in the HTML. In `classroom.js`, check `event.type`. If it is not `mcq`, display the textarea instead of `options-list` and grab its value on submit.

### Issue 4: Incorrect MODIFY → REGENERATE → HUMAN Behavior
- **Affected Component:** `modules/ai_agent_orchestration/src/agents/adaptation_controller.py`
- **Evidence:** `AdaptationController.decide` counts consecutive failures by explicitly matching `ev.node_id == node_id`.
- **Cause:** When the system triggers `REGENERATE`, a completely new lesson plan is generated. This creates new nodes with new `node_id`s. When the student fails the new node, the failure counter resets to 1 (because the new `node_id` doesn't match the old failures in `session_history`). Therefore, the controller triggers `MODIFY` instead of escalating.
- **Proposed Solution:** Update the failure counting logic in `adaptation_controller.py` to simply count consecutive failures at the tail of `session_history` regardless of `node_id`. Since a student cannot advance to a new node without answering correctly, any consecutive failures at the tail inherently belong to the current concept roadblock.

## 6. Implementation Plan

**Step 1 — Static/Dynamic Frontend Audit Fixes**
- Clear placeholder data from `classroom.html` (e.g. `Biology_Notes.pdf`, hardcoded citations).
- Ensure initial UI loads cleanly until the websocket populates it.

**Step 2 — Video Controls**
- Add `controls` to `<video id="lesson-video">`.
- Remove the `.video-controls-bar` overlay to rely on native, bug-free browser controls.

**Step 3 — Free-Form Answer**
- Add `<textarea id="free-form-answer" class="free-form-input" style="display:none;"></textarea>` to `checkpoint-card`.
- Modify `classroom.js` to inspect `event.type`. Toggle visibility between `.options-list` and `#free-form-answer`.
- Modify the `btn-check-answer` event listener to read from the visible input and pass the correct payload.

**Step 4 — Adaptation Integration**
- Modify `modules/ai_agent_orchestration/src/agents/adaptation_controller.py`.
- Remove the `ev.node_id == node_id` restriction when calculating the `failures` counter. Iterate backwards through `session_history` and strictly count consecutive `not ev.correct` entries.

**Step 5 — Final E2E Verification**
- Define the human-run verification matrix to ensure all components tie together successfully.

## 7. Contract Preservation
The following contracts will remain **strictly unchanged**:
- `InteractionEvent` schema
- `StudentResponse` schema
- `EvaluationResult` schema
- `AdaptationDecision` schema
- Websocket event typings (e.g., `student_response`, `adaptation_decision`)

## 8. Testing Plan
- **Static UI:** Visually confirm the UI doesn't show fake biology notes on load.
- **Video:** Click play, pause, and seek on the native video player.
- **Free-Form:** Verify the textarea renders for a `short_answer` question, allows typing, and submits successfully.
- **Adaptation:** Manually test 3 consecutive failures. Verify the sequence exactly: `MODIFY` (1) → `REGENERATE` (2) → `HUMAN` (3).

## 9. Deferred Improvements
- Visual polish, CSS styling, and responsive layout overhauls.
- Avatar visual realism and viseme syncing quality.
- Enhancing generated visual equation aesthetics.
- Custom video players/scrubbers (sticking to native HTML5 for stability).

## 10. Remaining E2E Risks
- External API rate limits (Gemini/Edge-TTS) during heavy testing load.
- Potential race conditions if a user clicks the "Check my answer" button multiple times before the websocket responds (will disable button on submit to mitigate).

## 11. Frontend Audit: Data Sources & Model Access
- **Data Provenance**: The frontend correctly pulls data from WebSocket events mapped directly to ML Core, RAG, and AI Agent Orchestration pipelines. Initial states are now cleanly represented by loading indicators (e.g., WAITING or Connecting to teaching session...) instead of static mock data.
- **API Keys & Model Access**: The frontend does not make direct calls to Gemini or Edge-TTS. All LLM/TTS interactions correctly happen server-side (ackend -> i_agent_orchestration), protecting API keys and ensuring the architecture remains secure.
- **UI Display Fidelity**: Real-time telemetry (Confidence, Pedagogical Adaptation, State transitions) accurately represents backend FSM progression. The UI seamlessly toggles dynamically between Multiple Choice options and free-form Textarea inputs based on the generated Interaction schema from the orchestrator.
- **Status**: Verified and Stable. Improvements successfully applied in Phase 2.
