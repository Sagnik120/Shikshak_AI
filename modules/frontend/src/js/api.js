/**
 * Shikshak AI — API Service Abstraction
 * Handles REST communication with the FastAPI backend with seamless mock fallback.
 */

const API_BASE_URL = window.location.origin.includes(":8000") 
  ? window.location.origin 
  : "http://127.0.0.1:8000";

export const api = {
  baseUrl: API_BASE_URL,

  async createSession() {
    try {
      const resp = await fetch(`${this.baseUrl}/api/v1/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      console.warn("Backend unavailable; using mock session:", err.message);
      return {
        session_id: "mock_session_" + Date.now().toString(36),
        token: "mock_jwt_token_shikshak",
        status: "created"
      };
    }
  },

  async submitTopic(sessionId, topic, constraints, token) {
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resp = await fetch(`${this.baseUrl}/api/v1/sessions/${sessionId}/topic`, {
        method: "POST",
        headers,
        body: JSON.stringify({ session_id: sessionId, topic, constraints }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      console.warn("Using mock topic response:", err.message);
      return { status: "success", session_id: sessionId, topic };
    }
  },

  async uploadDocument(sessionId, file, token) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const headers = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resp = await fetch(`${this.baseUrl}/api/v1/sessions/${sessionId}/upload`, {
        method: "POST",
        headers,
        body: formData,
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      console.warn("Upload document error:", err.message);
      return {
        status: "ready",
        document_id: "doc_" + Math.random().toString(36).substring(2, 8),
        filename: file.name,
        size_bytes: file.size,
        detected_structure: {
          chapters: ["Section 1: Foundations", "Section 2: Core Principles", "Section 3: Practical Review"],
          key_terms: []
        },
        detected_language: "English",
        confidence: 0.994
      };
    }
  },

  async generatePlan(sessionId, token) {
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resp = await fetch(`${this.baseUrl}/api/v1/sessions/${sessionId}/plan`, {
        method: "POST",
        headers,
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      console.warn("Using mock lesson plan:", err.message);
      return {
        lesson_id: "lesson_cell_structure_01",
        nodes: [
          { node_id: "node_1", concept: "What is a cell?", depth: "intro", est_minutes: 3, visual_type: "diagram", checkpoint_question: false },
          { node_id: "node_2", concept: "Cell theory", depth: "intro", est_minutes: 4, visual_type: "timeline", checkpoint_question: false },
          { node_id: "node_3", concept: "Cell membrane", depth: "core", est_minutes: 6, visual_type: "diagram", checkpoint_question: true },
          { node_id: "node_4", concept: "Transport across membrane", depth: "core", est_minutes: 8, visual_type: "equation", checkpoint_question: true },
          { node_id: "node_5", concept: "Cell organelles", depth: "core", est_minutes: 7, visual_type: "image", checkpoint_question: false },
          { node_id: "node_6", concept: "Plant vs. animal cells", depth: "advanced", est_minutes: 5, visual_type: "diagram", checkpoint_question: true },
          { node_id: "node_7", concept: "Checkpoint quiz", depth: "review", est_minutes: 4, visual_type: "code", checkpoint_question: true },
          { node_id: "node_8", concept: "Wrap-up & next steps", depth: "summary", est_minutes: 3, visual_type: "diagram", checkpoint_question: false }
        ]
      };
    }
  }
};
