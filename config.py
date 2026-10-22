"""
Central configuration.

Reads settings from the .env file (never hard-code keys!) and decides
which "brain" the agents use:

* LIVE mode  -> a real LLM (Groq, Llama 3.3 70B) through CrewAI
* DEMO mode  -> an offline, deterministic engine (no key / no internet needed)

Demo mode is used automatically when no GROQ_API_KEY is present, so the
project always runs for evaluators, tests and recordings.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Keep CrewAI quiet about telemetry - this is a student project
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true" or not GROQ_API_KEY
DEMO_DELAY = float(os.getenv("DEMO_DELAY", "0.6"))
CREW_VERBOSE = os.getenv("CREW_VERBOSE", "false").lower() == "true"

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "run_log.txt"
OUTPUT_DIR = BASE_DIR / "outputs"
SAMPLE_DIR = BASE_DIR / "sample_data"

# Recommendation thresholds used by the HR Summary Agent
HIRE_THRESHOLD = 75
MAYBE_THRESHOLD = 55


def mode_label() -> str:
    """Human-readable description of the active engine."""
    if DEMO_MODE:
        return "Demo mode (offline engine, no API key)"
    return f"Live mode (Groq - {GROQ_MODEL})"
