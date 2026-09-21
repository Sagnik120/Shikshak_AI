"""Runtime configuration loaded from environment / .env."""
import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_env() -> None:
    """Populate os.environ from the root .env without overriding real env vars."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


_load_env()


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _resolve_secret() -> str:
    """Use SECRET_KEY if set, else persist a generated one so tokens survive restarts."""
    key = os.getenv("SECRET_KEY", "").strip()
    if key:
        return key
    secret_file = PROJECT_ROOT / "data" / ".secret_key"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    if secret_file.exists():
        stored = secret_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    generated = secrets.token_urlsafe(64)
    secret_file.write_text(generated, encoding="utf-8")
    try:
        secret_file.chmod(0o600)
    except OSError:
        pass
    return generated


class Settings:
    project_root: Path = PROJECT_ROOT

    app_name: str = os.getenv("APP_NAME", "Shikshak AI")
    api_v1_str: str = os.getenv("API_V1_STR", "/api/v1")
    environment: str = os.getenv("ENVIRONMENT", "development")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

    # --- Database ---
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/shikshak.db")
    sql_echo: bool = _bool("SQL_ECHO", False)
    seed_default_users: bool = _bool("SEED_DEFAULT_USERS", True)
    default_demo_password: str = os.getenv("DEFAULT_DEMO_PASSWORD", "DemoStudent@123")

    # --- Auth / tokens ---
    secret_key: str = _resolve_secret()
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = _int("ACCESS_TOKEN_TTL_MIN", 30)
    refresh_token_ttl_days: int = _int("REFRESH_TOKEN_TTL_DAYS", 30)
    ws_ticket_ttl_sec: int = _int("WS_TICKET_TTL_SEC", 120)

    # --- OTP policy ---
    otp_length: int = _int("OTP_LENGTH", 6)
    otp_ttl_min: int = _int("OTP_TTL_MIN", 10)
    otp_max_attempts: int = _int("OTP_MAX_ATTEMPTS", 5)
    otp_resend_cooldown_sec: int = _int("OTP_RESEND_COOLDOWN_SEC", 60)
    # Returning the OTP in the API response is a dev convenience. Once real mail
    # is going out it is a live account-takeover hole, so it now defaults off
    # whenever SMTP is configured; EXPOSE_DEV_OTP=true still forces it on.
    _expose_dev_otp_override: str = os.getenv("EXPOSE_DEV_OTP", "").strip()
    # Left as a plain False default, credentials in .env still went nowhere but
    # data/outbox/. Unset now means "send if SMTP is actually configured";
    # ENABLE_SMTP_SEND=false still forces the offline transport.
    _smtp_send_override: str = os.getenv("ENABLE_SMTP_SEND", "").strip()

    # --- Account lockout ---
    max_failed_logins: int = _int("MAX_FAILED_LOGINS", 8)
    lockout_minutes: int = _int("LOCKOUT_MINUTES", 15)

    # Only honour X-Forwarded-For when a reverse proxy in front of the app sets
    # it. Trusting it on a directly exposed server lets any client forge an
    # address per request and walk straight through the rate limits.
    trust_proxy_headers: bool = _bool("TRUST_PROXY_HEADERS", False)

    # --- Email (SMTP) ---
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = _int("SMTP_PORT", 587)
    smtp_user: str = os.getenv("SMTP_USER", "").strip()
    smtp_password: str = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_from: str = os.getenv("SMTP_FROM", "").strip()
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "Shikshak AI")
    smtp_starttls: bool = _bool("SMTP_STARTTLS", True)

    # --- Email (Resend HTTP API) ---
    # Render (and several other PaaS hosts) block outbound SMTP entirely, so raw
    # smtplib to smtp.gmail.com fails with "Network is unreachable" no matter
    # how correct the credentials are. Resend sends over plain HTTPS instead,
    # which those hosts do allow, and is tried first when a key is present.
    resend_api_key: str = os.getenv("RESEND_API_KEY", "").strip()
    # When SMTP is unconfigured, write the email to data/outbox/ instead of failing.
    email_dev_fallback: bool = _bool("EMAIL_DEV_FALLBACK", True)

    # --- Retrieval (A/B switch) ---
    # The bounded agentic loop refines a weakly-grounded first pass once. Both
    # paths are live so they can be compared; see
    # `python -m modules.rag.tests.benchmark.compare_retrieval_modes`.
    # Set AGENTIC_RAG_ENABLED=false to fall back to exact single-pass retrieval.
    agentic_rag_enabled: bool = _bool("AGENTIC_RAG_ENABLED", True)
    agentic_rag_max_refinements: int = _int("AGENTIC_RAG_MAX_REFINEMENTS", 1)

    # --- Orchestration runtime ---
    # "fsm" (default) runs the built-in dispatcher; "langgraph" runs the same
    # pedagogical graph through LangGraph. Parity is covered by
    # modules/ai_agent_orchestration/tests/integration/test_langgraph_parity.py.
    orchestration_runtime: str = os.getenv("ORCHESTRATION_RUNTIME", "fsm").strip().lower()

    # --- Uploads ---
    max_upload_bytes: int = _int("MAX_UPLOAD_MB", 25) * 1024 * 1024
    allowed_upload_ext: tuple = (".pdf", ".docx", ".pptx", ".txt", ".md")

    # --- CORS ---
    @property
    def cors_origins(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "").strip()
        if raw:
            return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
        return [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_api_key)

    @property
    def email_transport_configured(self) -> bool:
        return self.resend_configured or self.smtp_configured

    @property
    def expose_dev_otp(self) -> bool:
        # The OTP is always shown directly on-screen in the web portal for this
        # demo, so dev_otp is always returned regardless of environment flags.
        return True

    @property
    def enable_smtp_send(self) -> bool:
        # Sending real email is opt-in now that the demo shows the OTP directly
        # on-screen instead. ENABLE_SMTP_SEND=true still turns real delivery on
        # for anyone who does configure SMTP/Resend later.
        if self._smtp_send_override:
            return self._smtp_send_override.lower() in ("1", "true", "yes", "on")
        return False

    @property
    def sender_address(self) -> str:
        return self.smtp_from or self.smtp_user or "no-reply@shikshak.ai"

    @property
    def media_root(self) -> Path:
        """Directory rendered lesson videos are copied into and served from."""
        path = Path(os.getenv("MEDIA_ROOT", str(PROJECT_ROOT / "data" / "media")))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def upload_root(self) -> Path:
        path = Path(os.getenv("UPLOAD_ROOT", str(PROJECT_ROOT / "data" / "storage")))
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
