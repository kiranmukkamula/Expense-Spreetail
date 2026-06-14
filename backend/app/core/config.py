import os
from dotenv import load_dotenv

# Load environmental variables from .env file
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Split Expenser API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretjwtkeythatissharedandsecure123!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./split_expenser.db")

settings = Settings()
