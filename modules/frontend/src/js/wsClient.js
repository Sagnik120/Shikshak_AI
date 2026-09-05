/**
 * Shikshak AI — WebSocket Session Client (Real & Mock Replay Engine)
 * Implements Contract-compliant live streaming and a 14-step mock event replay sequence.
 */

export class ShikshakWSClient {
  constructor(sessionId, token, mode = "mock") {
    this.sessionId = sessionId;
    this.token = token;
    this.mode = mode;
    this.handlers = {};
    this.ws = null;
    this.isConnected = false;
    this.mockStep = 0;
    this.pendingUserResponseResolver = null;
  }

  on(eventType, handler) {
    if (!this.handlers[eventType]) {
      this.handlers[eventType] = [];
    }
    this.handlers[eventType].push(handler);
  }

  emit(eventType, data) {
    const listeners = this.handlers[eventType] || [];
    listeners.forEach((fn) => {
      try {
        fn(data);
      } catch (err) {
        console.error(`Error in handler for ${eventType}:`, err);
      }
    });
  }

  connect() {
    if (this.mode === "mock") {
      this._startMockReplay();
      return;
    }

    // Live WebSocket connection to FastAPI backend
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host.includes(":8000") ? window.location.host : "127.0.0.1:8000";
    const wsUrl = `${protocol}//${host}/api/v1/sessions/${this.sessionId}/live?token=${this.token || ""}`;

    console.log("[WS] Connecting to:", wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      this.emit("connection_status", { status: "connected" });
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.log("[WS IN]", msg.event_type, msg.payload);
        this.emit(msg.event_type, msg.payload);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.emit("connection_status", { status: "offline" });
    };

    this.ws.onerror = (err) => {
      console.warn("WebSocket error; switching to mock replay:", err);
      this.mode = "mock";
      this._startMockReplay();
    };
  }

  send(message) {
    console.log("[WS OUT]", message.event_type, message.payload);
    if (this.mode === "mock") {
      if (this.pendingUserResponseResolver) {
        this.pendingUserResponseResolver(message);
        this.pendingUserResponseResolver = null;
      }
      return;
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /* --------------------------------------------------------------------------
     14-STEP SCRIPTED MOCK REPLAY SEQUENCE
     -------------------------------------------------------------------------- */
  async _startMockReplay() {
    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    // 1. Session Ready
    await delay(400);
    this.isConnected = true;
    this.emit("connection_status", { status: "connected" });
    this.emit("session_ready", { session_id: this.sessionId, topic: "Cell Membrane & Transport" });

    // 2. TEACH (Initial explanation for Node 3: Cell Membrane)
    await delay(800);
    this.emit("ai_state", { state: "TEACH", node_id: "node_3", concept: "Cell membrane" });
    this.emit("video_segment", {
      node_id: "node_3",
      title: "Cell Membrane: The Selective Doorway",
      script_text: "The cell membrane acts as a selective doorway, not a rigid wall. It is the cell's first decision-maker, carefully choosing what materials can enter and leave.",
      highlight_phrase: "first decision-maker",
      duration_sec: 14.5,
      avatar_cue: "emphasis",
      visual_spec: {
        type: "diagram",
        content: "Phospholipid Bilayer & Protein Channels"
      },
      video_url: "" // Triggers fallback whiteboard animation in UI
    });

    // 3. Subtitle update
    await delay(1200);
    this.emit("subtitle_update", {
      text: "The cell membrane is a selective doorway, not a wall. It is the cell's first decision-maker.",
      highlight: "first decision-maker"
    });

    // 4. INTERACT
    await delay(2000);
    this.emit("ai_state", { state: "INTERACT", node_id: "node_3" });

    // 5. First checkpoint appears
    this.emit("interaction_event", {
      node_id: "node_3",
      question_text: "Which phrase best describes the role of the cell membrane?",
      type: "mcq",
      options: [
        "It stores the cell's genetic code.",
        "It controls what enters and leaves the cell.",
        "It creates energy from sunlight."
      ],
      expected_concept: "It controls what enters and leaves the cell."
    });

    // Wait for user's response
    const firstResponse = await new Promise((resolve) => {
      this.pendingUserResponseResolver = resolve;
    });

    // 6. Evaluate first response (handles both correct and wrong answers)
    this.emit("ai_state", { state: "EVALUATE" });
    await delay(700);

    const isFirstCorrect = firstResponse.payload.raw_answer === "It controls what enters and leaves the cell.";

    if (!isFirstCorrect) {
      // 7. ADAPT: Incorrect answer
      this.emit("evaluation_result", {
        node_id: "node_3",
        correct: false,
        confidence: 0.91,
        feedback_text: "Not quite — the cell's genetic code is safely stored inside the nucleus, not the outer membrane."
      });

      // 8. MODIFY decision
      await delay(900);
      this.emit("adaptation_decision", {
        action: "MODIFY",
        target_node_id: "node_3",
        reason: "Misconception detected: confused membrane with nucleus. Retargeting with doorway analogy."
      });

      // 9. Reteaching explanation
      await delay(1200);
      this.emit("ai_state", { state: "TEACH" });
      this.emit("video_segment", {
        node_id: "node_3",
        title: "Adaptive Scaffolding: Doorway Analogy",
        script_text: "Let's make the idea smaller: imagine the membrane as a selective doorway, not a wall. Just like a doorway has a lock and key, the membrane decides which materials can pass through and which must stay out.",
        highlight_phrase: "selective doorway",
        duration_sec: 12.0,
        avatar_cue: "encouraging",
        visual_spec: {
          type: "diagram",
          content: "Semi-permeable Doorway Concept"
        }
      });

      // 10. Retry checkpoint
      await delay(2200);
      this.emit("ai_state", { state: "INTERACT" });
      this.emit("interaction_event", {
        node_id: "node_3",
        question_text: "If the membrane is a selective doorway, what does it decide?",
        type: "mcq",
        options: [
          "Which materials can pass through.",
          "How much sunlight reaches the cell.",
          "When the cell reproduces."
        ],
        expected_concept: "Which materials can pass through."
      });

      // Wait for second answer
      await new Promise((resolve) => {
        this.pendingUserResponseResolver = resolve;
      });

      // 11. Correct answer on retry
      this.emit("ai_state", { state: "EVALUATE" });
      await delay(600);
      this.emit("evaluation_result", {
        node_id: "node_3",
        correct: true,
        confidence: 0.98,
        feedback_text: "Spot on! The membrane selectively permits nutrients and blocks harmful substances."
      });

      await delay(700);
      this.emit("adaptation_decision", {
        action: "ALLOW",
        target_node_id: "node_3",
        reason: "Concept mastered after analogy adaptation."
      });
    } else {
      // Direct correct answer on first try
      this.emit("evaluation_result", {
        node_id: "node_3",
        correct: true,
        confidence: 0.95,
        feedback_text: "Exact! The membrane acts as a selective barrier regulating transport."
      });
      await delay(600);
      this.emit("adaptation_decision", {
        action: "ALLOW",
        target_node_id: "node_3",
        reason: "Student answered correctly on first attempt."
      });
    }

    // 12. ASSESS
    await delay(1200);
    this.emit("ai_state", { state: "ASSESS" });
    this.emit("assessment_report", {
      lesson_id: "lesson_cell_structure_01",
      topic: "Cell Structure & Transport",
      score_pct: 78.0,
      strong_areas: ["Cell theory", "Selective permeability", "Organelle roles"],
      weak_areas: ["Diffusion vs. osmosis", "Active transport"],
      recommended_next: [
        "Replay the tricky questions",
        "Learn active transport",
        "Review your saved notes"
      ],
      narrative_feedback: "You initially hesitated on the membrane's core role, but once we grounded it with the selective doorway analogy, you correctly identified nutrient gating in under 4 seconds. Great intuition on passive transport."
    });

    // 13. Session complete
    await delay(1500);
    this.emit("session_complete", {
      redirect_url: "report.html"
    });
  }
}
