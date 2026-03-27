"""Agent runtime configuration."""

from pydantic_settings import BaseSettings


class AgentConfig(BaseSettings):
    # SGMC Brain API (the system of record)
    BRAIN_API_URL: str = "http://127.0.0.1:8090/api"

    # GOV.UK APIs for MHRA ingestion
    GOVUK_SEARCH_URL: str = "https://www.gov.uk/api/search.json"
    GOVUK_CONTENT_URL: str = "https://www.gov.uk/api/content"

    # Agent settings
    MHRA_POLL_HOURS: int = 4
    HAIKU_MODEL: str = "haiku"
    SONNET_MODEL: str = "sonnet"

    # Cost guardrails
    MAX_BUDGET_INGESTION: float = 0.20  # $0.20 per ingestion run
    MAX_BUDGET_TRIAGE: float = 0.10  # $0.10 per event triage
    MAX_BUDGET_NARRATOR: float = 0.50  # $0.50 per narrative generation

    model_config = {"env_prefix": "AGENT_", "env_file": ".env", "extra": "ignore"}


config = AgentConfig()
