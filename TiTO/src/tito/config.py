import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from typing import cast

load_dotenv()


@dataclass
class Settings:
    database_url: str
    queue_table: str = "job_queue"
    callback_queue: str = "callback_queue"
    max_jobs: int = 10
    timeout_seconds: int = 300
    schema_version: str = "1.0"
    api_url: str = "http://localhost:5001"
    api_tokens: list[str] = field(default_factory=list)
    api_token_roles: dict[str, str] = field(default_factory=dict)
    jwt_secret: str | None = None
    jwt_algorithms: list[str] = field(default_factory=lambda: ["HS256"])
    jwt_audience: str | None = None
    jwt_issuer: str | None = None

    timezone: str = "UTC"

    max_retries: int = 3
    retry_base_delay: int = 5  # seconds, exponential backoff: 5, 10, 20, ...
    callback_max_attempts: int = 3
    callback_retry_delay: int = 60  # seconds between callback retries

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env_dict = cast(dict[str, str], env or os.environ)
        token_string = env_dict.get("API_TOKENS", env_dict.get("API_TOKEN", ""))
        tokens = [token.strip() for token in token_string.split(",") if token.strip()]

        roles_string = env_dict.get("API_TOKEN_ROLES", "")
        roles: dict[str, str] = {}
        for item in roles_string.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" in item:
                token, role = item.split("=", 1)
                roles[token.strip()] = role.strip()

        if tokens and not roles:
            roles = {token: "admin" for token in tokens}
        elif roles and not tokens:
            tokens = list(roles.keys())

        algorithms_string = env_dict.get("JWT_ALGORITHMS", "HS256")
        algorithms = [alg.strip() for alg in algorithms_string.split(",") if alg.strip()]

        return cls(
            timezone=env_dict.get("TIMEZONE", "UTC"),
            database_url=env_dict.get("DATABASE_URL", "sqlite:///tito.db"),
            queue_table=env_dict.get("QUEUE_TABLE", "job_queue"),
            callback_queue=env_dict.get("CALLBACK_QUEUE", "callback_queue"),
            max_jobs=int(env_dict.get("MAX_JOBS", "10")),
            timeout_seconds=int(env_dict.get("TIMEOUT_SECONDS", "300")),
            schema_version=env_dict.get("SCHEMA_VERSION", "1.0"),
            api_url=env_dict.get("API_URL", "http://localhost:5001"),
            api_tokens=tokens,
            api_token_roles=roles,
            jwt_secret=env_dict.get("JWT_SECRET"),
            jwt_algorithms=algorithms,
            jwt_audience=env_dict.get("JWT_AUDIENCE"),
            jwt_issuer=env_dict.get("JWT_ISSUER"),
            max_retries=int(env_dict.get("MAX_RETRIES", "3")),
            retry_base_delay=int(env_dict.get("RETRY_BASE_DELAY", "5")),
            callback_max_attempts=int(env_dict.get("CALLBACK_MAX_ATTEMPTS", "3")),
            callback_retry_delay=int(env_dict.get("CALLBACK_RETRY_DELAY", "60")),
        )
