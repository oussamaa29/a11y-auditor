import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./a11y_auditor.db")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5174").split(",")
    SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "45"))
    # Chaque scan lance un Chrome (~300 Mo de RAM) : au-delà, la requête est refusée (503)
    MAX_CONCURRENT_SCANS: int = int(os.getenv("MAX_CONCURRENT_SCANS", "2"))
    # À n'activer que dans un conteneur lancé en root, où le bac à sable de Chrome ne démarre pas
    CHROME_NO_SANDBOX: bool = os.getenv("CHROME_NO_SANDBOX", "false").lower() in ("1", "true", "yes")


settings = Settings()
