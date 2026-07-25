import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./a11y_auditor.db")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5174").split(",")
    SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "45"))


settings = Settings()
