# Setup Commands

This document contains the step-by-step commands required to set up, test, and run the currently implemented components (RAG and Avatar/Voice) of the Shikshak AI project.

## 1. Environment / Prerequisites
- **Python**: 3.9+ recommended
- **OS**: Cross-platform (commands below are for Windows/PowerShell)
- FFmpeg (must be installed and available in system PATH for `avatar_voice` compositor)

## 2. Virtual Environment Setup
```powershell
# Create a virtual environment
python -m venv venv

# Activate the virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

## 3. Dependency Installation
```powershell
# Install all required Python packages
pip install -r requirements.txt
```

## 4. Environment Variables / Configuration
The following environment variables can optionally be configured (no secrets/API keys are currently required since local models are used):
- `CHROMA_PERSIST_DIR`: Path to save the Chroma vector database (defaults to `./chroma_db`)
- `WAV2LIP_CHECKPOINT_PATH`: Path to the Wav2Lip model checkpoint for the avatar (defaults to `""`, which may require passing explicit paths during initialization if used).

## 5. Commands to Run the Project
The main `backend` API and `frontend` UI are not yet implemented. Execution is currently limited to diagnostic scripts for the implemented modules.

## 6. Commands to Run Tests
The repository uses `pytest` for unit testing.
```powershell
# Run all configured tests (as defined in pytest.ini)
pytest

# Run tests with verbose output
pytest -v
```

## 7. Diagnostics / Checks
To verify that the RAG and Avatar/Voice pipelines are functioning correctly (these will download HuggingFace models on first run):

```powershell
# Run RAG module diagnostics (chunking, embedding, retrieval)
python scripts/run_rag_diagnostics.py

# Run Avatar & Voice diagnostics (TTS, visual generation, video compositing)
python scripts/run_avatar_voice_diagnostics.py
```

## 8. External-Service Setup
- No external SaaS API keys (e.g., OpenAI, Anthropic) are currently required. The existing implementations use local HuggingFace/SentenceTransformers models for embeddings and local TTS models.
- **Note**: The first time you run tests or diagnostics, significant time and disk space will be required to download the pre-trained ML models.

## 9. Recommended Execution Order (Fresh Setup)
1. Ensure Python and FFmpeg are installed.
2. Run Virtual Environment Setup.
3. Run Dependency Installation.
4. Run `pytest` to ensure unit tests pass.
5. Run `python scripts/run_rag_diagnostics.py` to verify the RAG pipeline.
6. Run `python scripts/run_avatar_voice_diagnostics.py` to verify the video rendering pipeline.
