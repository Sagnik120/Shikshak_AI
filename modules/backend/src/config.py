import os

class Settings:
    app_name: str = os.getenv("APP_NAME", "Shikshak AI Backend")
    api_v1_str: str = os.getenv("API_V1_STR", "/api/v1")

settings = Settings()
