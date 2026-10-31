import os
from typing import Literal

class Config:
    PROVIDER_MODE: Literal["offline", "live"] = os.getenv("PROVIDER_MODE", "offline")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "gpt-4o-mini")
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
    RECOVERY_BACKOFF_SECONDS: float = float(os.getenv("RECOVERY_BACKOFF_SECONDS", "0.1"))
    EVALUATION_REFERENCE_DATE: str = os.getenv("EVALUATION_REFERENCE_DATE", "2025-01-15")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")

    @classmethod
    def validate(cls):
        if cls.PROVIDER_MODE == "live" and not cls.LLM_API_KEY:
            raise ValueError("LLM_API_KEY required for live provider mode")
