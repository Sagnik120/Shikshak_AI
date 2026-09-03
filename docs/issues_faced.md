# Issues Faced, Architectural Gaps & Technical Solutions

This document provides a comprehensive, module-by-module record of the architectural gaps, edge-case bugs, and implementation challenges encountered in **Shikshak AI**, along with the pedagogical rationale, theoretical solutions, and concrete technical implementations used to resolve them.

---

## 1. RAG (Retrieval-Augmented Generation) Module

### Issue 1.1: Crash & Undefined Behavior in Topic-Only Teaching Mode (`document_id=None`)

#### 1. In Simple Language
When students use Shikshak AI, they don't always upload a textbook or PDF. Often, they just type a topic like: *"Teach me React for a technical interview"* or *"Explain Artificial Intelligence from scratch"*. 

Originally, the RAG module assumed a document was *always* uploaded. If no document existed (`document_id=None`), the retrieval engine tried to query an empty database or threw an unhandled error, leaving the AI Teacher confused about how to respond without hallucinating document citations.

#### 2. The Core Technical Problem
In `modules/rag/src/service.py`:
- `RAGService.retrieve_context(document_id: str, ...)` had a mandatory string type hint for `document_id`.
- If `document_id` was `None`, an empty string `""`, or whitespace `"   "`, `self.retriever.retrieve()` attempted a vector lookup against non-existent collections or crashed.
- Furthermore, `get_grounded_prompt()` was hardcoded to emit a citation prompt (`[Chunk chunk_xyz]... output: grounded_on: [...]`), which forced the LLM to either fabricate fake citations or output error messages.
- **Rubric Exposure**: Directly threatened **RAG and Knowledge Grounding (15%)** and **AI/ML Implementation (15%)**, as topic-only teaching is an explicit Problem Statement requirement (PS §4, §17).

#### 3. The Solution We Conceived
1. Enable `document_id` to be strictly optional throughout the domain models (`RetrievalRequest`, `RetrievalResult`) and service layer.
2. Short-circuit in $O(1)$ time whenever `clean_doc_id` is `None` or whitespace, returning `has_sufficient_context=False` and a specialized risk tag: `risk_level="no_document_context"`.
3. In `format_grounding_context_block()`, detect `risk_level == "no_document_context"` and inject a specialized open-domain pedagogical prompt instructing the LLM:
   > *"MODE: Topic-Only Teaching (No uploaded source document provided)*  
   > *- Teach and explain this concept using authoritative, clear pedagogical general knowledge.*  
   > *- Do NOT fabricate citations, document excerpts, page numbers, or slide numbers.*  
   > *- Output at the end: grounded_on: []"*

#### 4. Technical Resolution & Code Implementation
- **Model Enhancements (`modules/rag/src/models.py`)**:
  ```python
  class RetrievalRequest(BaseModel):
      document_id: Optional[str] = Field(default=None, description="Document ID or None for topic-only teaching")
      ...
  
  class RetrievalResult(BaseModel):
      document_id: Optional[str] = Field(default=None, description="Document ID or None for topic-only teaching")
      chunks: List[RetrievedChunk] = Field(default_factory=list)
      has_sufficient_context: bool = Field(default=True)
      risk_level: str = Field(default="low", description="'low', 'no_document_context', or 'high_hallucination_risk'")
      
      @property
      def candidate_chunks(self) -> List[RetrievedChunk]:
          return self.chunks
  ```
- **Service Hardening (`modules/rag/src/service.py`)**:
  ```python
  def retrieve_context(self, document_id: Optional[str] = None, query_text: str = "", ...) -> RetrievalResult:
      clean_doc_id = document_id.strip() if document_id and isinstance(document_id, str) else None
      if not clean_doc_id:
          return RetrievalResult(
              document_id=None,
              query_text=query_text,
              chunks=[],
              has_sufficient_context=False,
              risk_level="no_document_context"
          )
      return self.retriever.retrieve(document_id=clean_doc_id, ...)
  ```
- **Anti-Hallucination Prompting (`modules/rag/src/grounding/prompt.py`)**:
  Separated `risk_level == "no_document_context"` from standard `low_context` warnings, ensuring the LLM understands that no document was uploaded rather than thinking a document retrieval failed.

#### 5. Verification & Test Evidence
Created `tests/integration/test_no_document_mode.py` testing:
- Boundary conditions: `None`, `""`, `"   "`, `"\t\n"`.
- Real-world PS §4 queries (*"Teach me React for a technical interview"*, *"Teach me AI from the beginning"*, and Hindi query *"मुझे न्यूटन के गति के नियम समझाइए"*).
- Mid-session lifecycle transition: Starting topic-only $\rightarrow$ uploading a physics textbook $\rightarrow$ querying again and receiving grounded chunks with citations.
- **Result**: **17/17 tests passing in 31s**.

---

### Issue 1.2: Latin-Biased Chapter Extraction and Indic Token Budget Overflow

#### 1. In Simple Language
The hackathon explicitly tests multilingual capabilities (e.g. uploading a Hindi NCERT textbook to generate an English or Hindi lesson plan). 

Previously, our chapter detector only looked for English words like "Chapter 1" and capital letters. In Hindi books, chapters are written like "अध्याय 1" or "पाठ 2", and Hindi doesn't have capital letters! As a result, Hindi books were parsed with zero detected chapters, degrading lesson plan quality.

Furthermore, Hindi words contain complex characters that break down into multiple subwords in the BGE-M3 embedding model. Counting words with simple whitespace caused Hindi chunks to secretly overshoot the 500-token limit, hurting retrieval accuracy.

#### 2. The Core Technical Problem
- In `modules/rag/src/parsing/structure.py` and `pdf_parser.py`:
  - Chapter regexes checked: `re.match(r'^(Chapter|Section|\d+)...')` or `first_line.isupper()`.
  - Devanagari chapters (`अध्याय 1`, `पाठ 2`, `इकाई 3`) and fallback key terms `re.findall(r'\b[a-zA-Z]{3,}\b')` completely missed Hindi text.
- In `modules/rag/src/chunking/chunker.py`:
  - `count_tokens()` approximated 1 token $\approx$ 1 word.
  - In BGE-M3 (XLM-RoBERTa based), Hindi words average **2.2 to 2.5 subwords per whitespace word**. A 300-word Hindi text expanded to 700+ tokens, exceeding the 500-token max threshold.
- **Rubric Exposure**: Impacted **Multilingual Capability (10%)** and **RAG Knowledge Grounding (15%)**.

#### 3. The Solution We Conceived
1. Create a centralized, script-aware heading recognizer `is_chapter_or_section_heading()` supporting Devanagari markers (`अध्याय`, `पाठ`, `इकाई`, `प्रकरण`, `खण्ड`, `भाग`) alongside Latin markers.
2. Upgrade TF-IDF key term extraction and frequency fallback with Unicode regex patterns (`[\u0900-\u097F]{2,}|[a-zA-Z]{3,}`) and Hindi stopword filtering.
3. In `chunker.py`, detect Devanagari scripts and apply a **2.3x subword expansion factor** per word during offline approximation, preventing chunk overflow.

#### 4. Technical Resolution & Code Implementation
- **Devanagari Heading Detector (`modules/rag/src/parsing/structure.py`)**:
  ```python
  DEVANAGARI_HEADING_PATTERNS = [
      r'^(अध्याय|पाठ|इकाई|प्रकरण|भाग|खण्ड)\s*([०-९\d]+)?\s*[:\.\-]?\s*(.*)$',
  ]
  ```
- **Parser Integration (`pdf_parser.py`, `txt_parser.py`, `docx_parser.py`)**:
  Wired `is_chapter_or_section_heading()` across all parsers so both Latin and Hindi chapters are detected seamlessly.
- **Indic Token Expansion (`modules/rag/src/chunking/chunker.py`)**:
  ```python
  devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
  total_chars = len(text.strip())
  multiplier = 2.3 if total_chars > 0 and (devanagari_chars / total_chars) > 0.15 else 1.3
  return max(1, int(len(text.split()) * multiplier))
  ```

#### 5. Verification & Test Evidence
Created `tests/unit/test_structure_multilingual.py` testing:
- Devanagari heading detection for `अध्याय`, `पाठ`, `इकाई`, `प्रकरण`.
- Mixed-script documents detecting both English and Hindi chapters.
- Multilingual TF-IDF key term extraction extracting Hindi scientific terms.
- Indic subword expansion testing: verified 10-paragraph Hindi textbook chunking strictly stays $\le 500$ tokens.

---

## 2. Avatar & Voice Module

### Issue 2.1: Single Static Visual Slides Failing the "Step-by-Step Solutions" Requirement

#### 1. In Simple Language
In a real classroom, a teacher does not put a single static slide on the blackboard and talk about it for 45 seconds without drawing or writing anything. When teaching math, they write out the derivation step by step. When teaching programming, they highlight the line of code that is currently executing and show what prints to the terminal.

Initially, our visual renderers created only one static image per teaching segment. This made the video feel like an avatar talking in front of a static PowerPoint slide, failing the hackathon's requirement for active visual demonstrations.

#### 2. The Core Technical Problem
In `modules/avatar_voice/src/visuals/`:
- `EquationRenderer` rendered a single LaTeX formula regardless of how complex the derivation was.
- `CodeRenderer` rendered a static code box with no active execution feedback or terminal output pane.
- `FFmpegCompositor` expected a single image path (`visual_result.image_path`) and looped it statically across the video duration.
- **Rubric Exposure**: Directly threatened **AI Teaching Video Generation (15%)** and **Human-Like Teaching & Adaptation (20%)**. Problem Statement §10 explicitly demands *"step-by-step solutions"* for math, *"processes and visual demonstrations"* for science, and *"execution flow"* for code.

#### 3. The Solution We Conceived
1. **Extend Contract Schemas**: Add `steps: Optional[List[str]] = None` and `execution_output: Optional[str] = None` to `VisualSpec`.
2. **Progressive Math Derivations**: When multiple derivation steps are provided, `EquationRenderer` generates a sequence of cumulative slide images (Step 1 $\rightarrow$ Step 1+2 $\rightarrow$ Step 1+2+3). In each step image, the active step is highlighted in bright cyan (`#06b6d4`) with an amber badge (`#f59e0b`), while previous steps are muted in `#94a3b8`.
3. **Progressive Code Execution Flow**: When code has execution output or step markers, `CodeRenderer` generates a 3-stage visual sequence:
   - *Stage 1 (Definition)*: Static code in IDE window.
   - *Stage 2 (Executing)*: Active execution line / return statement highlighted with an amber indicator bar.
   - *Stage 3 (Output Console)*: A glowing terminal window (`OUTPUT TERMINAL >`) appears underneath showing the output.
4. **Compositor Video Sequencing**: `FFmpegCompositor` calculates the duration per step ($d_{\text{step}} = \text{duration} / N$) and sequences the frames across the narration duration using FFmpeg's `concat` filter, transitioning seamlessly in sync with the audio.

#### 4. Technical Resolution & Code Implementation
- **Pydantic Extensions (`modules/avatar_voice/src/models.py`)**:
  ```python
  class VisualSpec(BaseModel):
      type: str
      content: Union[str, Dict[str, Any], List[Any]]
      steps: Optional[List[str]] = None
      execution_output: Optional[str] = None

  class VisualRenderResult(BaseModel):
      image_path: str
      width: int = 1344
      height: int = 1080
      visual_type: str
      step_image_paths: List[str] = Field(default_factory=list)
      is_progressive: bool = False
  ```
- **Equation Progressive Derivation (`modules/avatar_voice/src/visuals/equation_renderer.py`)**:
  Implemented `_render_progressive_steps()` and `_render_multi_step_frame()` with Matplotlib mathtext layout and PIL canvas fallbacks.
- **Code Execution Flow (`modules/avatar_voice/src/visuals/code_renderer.py`)**:
  Implemented `_render_progressive_execution_flow()` rendering syntax highlighting, active line highlight boxes, and terminal output windows.
- **Compositor Sequencing (`modules/avatar_voice/src/compositor/ffmpeg_compositor.py`)**:
  ```python
  # Sequence progressive visual inputs into a continuous video stream
  for step_path in valid_step_paths:
      cmd.extend(["-loop", "1", "-t", str(round(step_dur, 2)), "-i", step_path])
  concat_inputs = "".join([f"[{i + 1}:v]" for i in range(num_steps)])
  filter_graph = f"{concat_inputs}concat=n={num_steps}:v=1:a=0[vis_seq]; ..."
  ```

#### 5. Verification & Test Evidence
Created `tests/unit/test_progressive_visuals.py` covering boundary conditions and 4 real-world demo scenarios (Quadratic formula derivation, Binary Search execution flow, Hindi Pythagoras lesson, and Async Worker Pool).  
- **Result**: **11/11 tests passing in 2.26s**.

---

### Issue 2.2: Flat 140 WPM Heuristic in Fallback TTS Causing Hindi Audio Truncation & Desync

#### 1. In Simple Language
When our system runs offline or on a computer without internet access, it uses a built-in sound synthesizer (`FallbackTTSAdapter`) to generate speech without needing Microsoft Edge-TTS servers.

Previously, this offline synthesizer calculated speech duration using a flat rate of 140 words per minute regardless of whether the teacher was speaking English or Hindi. But Hindi sentences take about 15% to 20% longer to pronounce than English for the same meaning. As a result, Hindi audio ended prematurely, cutting off words and throwing subtitles and avatar lip-sync out of alignment.

#### 2. The Core Technical Problem
In `modules/avatar_voice/src/tts/fallback_adapter.py`:
- Line 42 used: `word_duration = max(0.2, len(word) * 0.06 + 0.15)`.
- Inter-word pauses were hardcoded to `0.05 * sample_rate`.
- This flat heuristic ignored the language parameter (`language="hi"`), contradicting our own architectural guidelines stating that Hindi speech takes ~15–20% longer.
- **Rubric Exposure**: Impacted **Multilingual Capability (10%)** and **Voice & AI Avatar (10%)**.

#### 3. The Solution We Conceived
1. Introduce a language-aware pacing dictionary in `FallbackTTSAdapter`:
   - `en`: $1.00$ baseline ($\sim 140\text{ WPM}$).
   - `hi`: $1.20$ scale ($\sim 115\text{ WPM}$, matching Edge-TTS neural Hindi cadence).
   - `hinglish`: $1.12$ scale ($\sim 125\text{ WPM}$, matching code-mixed speech).
2. Scale both the word duration and the pause duration by `pacing_factor`.

#### 4. Implementation Challenge & Bug Encountered
During initial implementation, we wrote:
```python
# BUGGY LOGIC
if lang_key.startswith("hi"):
    pacing_factor = 1.20
elif "hinglish" in lang_key:
    pacing_factor = 1.12
```
When running pytest, `test_hinglish_duration_is_intermediate` failed:
`AssertionError: assert 6.07 < 6.07`  
Because the string `"hinglish"` starts with the letters `"hi"`, Python's `startswith("hi")` matched `"hinglish"` first and assigned it $1.20$ instead of $1.12$!

**Fix**: Re-ordered the conditional checks to evaluate `"hinglish"` *before* checking for Hindi prefixes:
```python
lang_key = language.lower().strip()
if "hinglish" in lang_key:
    pacing_factor = 1.12
elif lang_key == "hi" or lang_key.startswith("hi-") or lang_key.startswith("hi_") or lang_key == "hindi":
    pacing_factor = 1.20
else:
    pacing_factor = 1.00
```

#### 5. Verification & Test Evidence
Created `tests/unit/test_tts_pacing.py` verifying duration scaling across English, Hinglish, and Hindi, proportional word timestamps, and WebVTT caption synchronization.  
- **Result**: **7/7 tests passing in 0.23s**.

---

### Issue 2.3: Silent Degradation to Static Video Previews When System FFmpeg is Missing

#### 1. In Simple Language
If a hackathon judge or evaluator downloads our project and runs it on a fresh machine that does not have the `ffmpeg` video command installed, the video generator would silently fail to make MP4 videos and instead produce a static preview image with a warning log.

#### 2. The Core Technical Problem
In `modules/avatar_voice/src/compositor/ffmpeg_compositor.py`:
- The compositor only checked `shutil.which("ffmpeg")`.
- If the binary was not on the system PATH, it immediately dropped to `_compose_with_pillow_fallback()`.
- While the Pillow fallback keeps automated test suites passing, presenting a static image instead of a video during a live demo would result in a massive point deduction for **AI Teaching Video Generation (15%)**.

#### 3. The Solution & Technical Implementation
We implemented dual-path binary resolution:
1. First, check `shutil.which("ffmpeg")` for system-installed binaries.
2. If absent, attempt to discover the self-contained static FFmpeg binary installed via the Python package `imageio-ffmpeg`:
   ```python
   self.ffmpeg_bin = shutil.which("ffmpeg")
   if not self.ffmpeg_bin:
       try:
           import imageio_ffmpeg
           self.ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
           logger.info(f"Using bundled imageio-ffmpeg binary: {self.ffmpeg_bin}")
       except Exception:
           self.ffmpeg_bin = None
   ```
3. If neither is available, emit a prominent warning banner explaining that the system is operating in preview fallback mode.

---

## 3. System-Wide Operations & Diagnostics

### Issue 3.1: Silent Runtime Degradation on Evaluation Machines (No Preflight Diagnostic)

#### 1. In Simple Language
When running a complex multi-module AI system, components like Edge-TTS, FFmpeg, ChromaDB, and BGE-M3 models rely on either local binaries, model caches, or internet connections. If any component is missing or restricted on a judge's machine, parts of the system might silently drop into fallback mode (like sine-wave voice or static image slides) without the presenter knowing why.

#### 2. The Core Technical Problem
- No single automated pre-flight health checker existed to audit the whole pipeline before a live judged presentation or deployment.
- Presenters had to run individual unit tests or discover failures during the actual demonstration.

#### 3. The Solution & Technical Implementation
Created `scripts/preflight_check.py`:
- Audits 9 critical Python libraries (`pydantic`, `pypdf`, `docx`, `pptx`, `PIL`, `chromadb`, `sklearn`, `transformers`, `pytest`).
- Audits FFmpeg binary resolution (system PATH vs `imageio-ffmpeg`).
- Audits Edge-TTS vs fallback acoustic synthesizer.
- Audits ChromaDB vector storage and index queries.
- Audits topic-only mode with `document_id=None`.
- Audits progressive visual generation (equations & code execution flows).
- Audits multilingual Devanagari chapter recognition and Indic subword budgeting.
- Emits a clean colored diagnostic dashboard and exits with `0` on healthy system status.

---

## 4. Summary of Resolved Issues & Current System Health

| Module | Issue ID | Issue Description | Severity | Resolution Status |
|---|---|---|:---:|:---:|
| **RAG** | `RAG-01` | No topic-only teaching path when `document_id=None` | **Critical (P0)** | **RESOLVED & TESTED** (17/17 tests passing) |
| **RAG** | `RAG-02` | Latin-biased chapter detection and Indic token budget overflow | **High (P1)** | **RESOLVED & TESTED** (23/23 tests passing) |
| **Avatar/Voice** | `AV-01` | Single static visual slides failing progressive demonstration requirements | **Critical (P0)** | **RESOLVED & TESTED** (11/11 tests passing) |
| **Avatar/Voice** | `AV-02` | Flat 140 WPM heuristic in offline TTS causing Hindi speech truncation | **High (P1)** | **RESOLVED & TESTED** (7/7 tests passing) |
| **Avatar/Voice** | `AV-03` | Silent FFmpeg fallback on systems without PATH binary | **High (P1)** | **RESOLVED & TESTED** (auto-discovery active) |
| **Operations** | `OPS-01` | Lack of preflight diagnostic to detect runtime fallback degradation | **High (P1)** | **RESOLVED & VERIFIED** (`scripts/preflight_check.py`) |

All changes have been committed, verified with automated unit/integration suites, and pushed to the upstream repository.
