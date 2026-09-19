# Web Test Details and Manual Execution Guide

This document details the available web-based testbeds for Shikshak AI. These testbeds are isolated diagnostic studios built to test individual components without needing the full system to be wired up. 

Below are highly detailed, step-by-step instructions on how to manually execute, inspect, and verify the health of each module.

---

## General Prerequisites
Before running **any** of the web tests below, ensure you have your environment ready:
1. **Open your Terminal (PowerShell/Bash)** at the root of the repository (`d:\Projects\Bharat_Academix_Hackathon_Shikshak_AI\Shikshak_AI`).
2. **Activate the Virtual Environment**:
   * Windows: `.\venv\Scripts\Activate.ps1`
   * Mac/Linux: `source venv/bin/activate`
3. **Check Dependencies**: Ensure `requirements.txt` is installed.
4. **Environment Variables**: Ensure `.env` is populated with necessary keys (e.g., LLM keys, TTS API keys) if required by the specific module.

---

## 1. AI Agent Orchestration Isolated Testbed
* **Purpose**: Test the core Finite State Machine (FSM), lesson planning, and teaching segment generation in isolation using mocked RAG/ML dependencies.
* **Priority**: P0

### Step-by-Step Execution:
1. **Start the Server**:
   ```bash
   python -m modules.ai_agent_orchestration.tests.web_test.server
   ```
2. **Open the Testbed**: Navigate your browser to `http://localhost:8001`.
3. **What to Check / Input**:
   * Locate the **Session / Topic Setup** section in the UI.
   * Enter a sample topic (e.g., "Newton's First Law").
   * Define Learner Constraints (e.g., "Grade 8, English").
   * Click **Generate Lesson Plan**.
4. **How to Verify (Success Criteria)**:
   * **In the UI**: You should see a structured `LessonPlan` JSON with multiple `LessonNode` elements. 
   * **State Transition**: Trigger the FSM to transition to `EXPLAIN`. It should generate a `TeachingSegment` (script, visual cues) for the first node.
   * **Check Terminal logs**: The server console should output state transitions (`PLANNING -> EXPLAINING -> EVALUATING`).
5. **Failure Indicators**:
   * 500 Internal Server Errors in the browser (check Terminal for Python tracebacks).
   * Infinite loops where the FSM never reaches the `ASSESSMENT` state.
   * Empty JSON responses or missing required fields (`script_text`, `visual_cue`).

---

## 2. RAG Isolated Testbed
* **Purpose**: Interactively test document parsing, chunking, embedding generation, and ChromaDB retrieval logic.
* **Priority**: P1

### Step-by-Step Execution:
1. **Start the Server**:
   ```bash
   python -m modules.rag.tests.web_test.server
   ```
2. **Open the Testbed**: Navigate your browser to `http://localhost:8002`.
3. **What to Check / Input**:
   * Navigate to the **Ingest/Upload** tab.
   * Upload a sample `.pdf` or `.docx` file containing educational content.
   * Navigate to the **Retrieve** tab.
   * Type a question related to the uploaded document (e.g., "What is the mitochondria?").
   * Click **Search / Retrieve**.
4. **How to Verify (Success Criteria)**:
   * **In the UI**: The retrieved context chunks should appear. They must be relevant to the query.
   * **Check Grounding**: If the UI has a Grounding Audit tab, verify that citations correctly map back to the source chunks.
   * **Terminal Logs**: Look for ChromaDB query logs and embedding latency metrics.
5. **Failure Indicators**:
   * Parsing crashes on specific PDFs (e.g., PyMuPDF errors).
   * Empty retrieval results (indicating embedding or ChromaDB insertion failed).

---

## 3. ML Core Isolated Testbed
* **Purpose**: Evaluate the NLP heuristics (answer scoring, misconception detection, visual suggestions).
* **Priority**: P1

### Step-by-Step Execution:
1. **Start the Server**:
   ```bash
   python -m modules.ml_core.tests.web_test.server
   ```
2. **Open the Testbed**: Navigate your browser to `http://localhost:8003`.
3. **What to Check / Input**:
   * Go to the **Evaluate Answer** section.
   * **Input Expected Concept**: "Velocity is a vector quantity having both magnitude and direction."
   * **Input Student Answer**: "Velocity is just how fast you go." (Intentional partial/wrong answer).
   * Click **Evaluate**.
4. **How to Verify (Success Criteria)**:
   * **In the UI**: You should receive an `EvaluationResult` JSON. 
   * **Check fields**: Verify `correct=False`, `partial_credit` is assigned, and a `misconception_tag` is identified (e.g., "confused_speed_velocity").
5. **Failure Indicators**:
   * Fallback to raw LLM failure or timeouts.
   * The evaluator universally returning `correct=True` for obviously wrong answers.

---

## 4. Avatar & Voice Isolated Testbed
* **Purpose**: Verify Text-to-Speech (TTS), visual renderers, and video compositing.
* **Priority**: P1
* **Prerequisites**: Ensure FFmpeg is installed and accessible in your system `PATH`.

### Step-by-Step Execution:
1. **Start the Server**:
   ```bash
   python -m modules.avatar_voice.tests.web_test.server
   ```
2. **Open the Testbed**: Navigate your browser to `http://localhost:8004`.
3. **What to Check / Input**:
   * Go to the **TTS Generation** or **Render** tab.
   * Enter a test script: "Welcome to Shikshak AI. Let's learn about fractions."
   * Select a visual type (e.g., "diagram").
   * Click **Render Video**.
4. **How to Verify (Success Criteria)**:
   * **In the UI**: The resulting video or audio stream should be playable directly in the browser.
   * **Terminal Logs**: You should see FFmpeg execution commands and processing percentage.
   * **Check output files**: Check the `data/avatar_voice_test_media/videos/` directory for the generated `.mp4` files.
5. **Failure Indicators**:
   * Missing API keys for external TTS/Avatar providers (e.g., Edge-TTS failing).
   * FFmpeg "Command not found" or codec errors in the terminal.

---

## 5. Backend API & WebSocket Testbed
* **Purpose**: Test the FastAPI REST endpoints and WebSocket relays (the true integration hub).
* **Priority**: P0

### Step-by-Step Execution:
1. **Start the Server**:
   ```bash
   python -m modules.backend.tests.web_test.server
   ```
2. **Open the Testbed**: Navigate your browser to `http://localhost:8005`.
3. **What to Check / Input**:
   * First, test the **REST API**: Click "Create Session". Ensure a `session_id` is returned.
   * Next, test the **WebSocket Relay**: Use the built-in WS tester in the UI. Connect to `ws://localhost:8005/api/v1/ws/{session_id}`.
   * Send a mock `StudentResponse` JSON through the WebSocket.
4. **How to Verify (Success Criteria)**:
   * **In the UI**: The WebSocket log should show "Connected". Messages sent should be echoed or responded to by the backend.
   * **Network Tab**: Open Browser DevTools (F12) -> Network -> WS. Verify the connection upgrades successfully (Status 101).
5. **Failure Indicators**:
   * WebSocket disconnects immediately (Code 1006).
   * 403/401 Unauthorized if token authentication fails.

---

## 6. Full Frontend Application (Standalone/Integrated)
* **Purpose**: Verify the actual user interface and fallback logic.
* **Priority**: P0

### Step-by-Step Execution:
1. **Start the Main Backend**:
   ```bash
   uvicorn modules.backend.src.main:app --port 8000
   ```
2. **Open the App**: Navigate your browser to `http://localhost:8000`.
3. **What to Check / Input**:
   * Click through the UI (select a preset topic or upload a document).
   * Open **Browser DevTools (F12) -> Console**.
4. **How to Verify (Success Criteria)**:
   * The UI renders correctly without styling breakages.
   * If the real backend routes are broken/unimplemented, the console will show `Backend unavailable; using mock session: ...` (from `api.js`), and the UI will continue functioning using mock data.
5. **Failure Indicators**:
   * Blank screen, React/JS errors in the browser console.
   * UI freezing because both the real backend call failed AND the mock fallback failed.
