import os
from dataclasses import dataclass
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

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env_dict = cast(dict[str, str], env or os.environ)
        return cls(
            database_url=env_dict.get("DATABASE_URL", "sqlite:///tito.db"),
            queue_table=env_dict.get("QUEUE_TABLE", "job_queue"),
            callback_queue=env_dict.get("CALLBACK_QUEUE", "callback_queue"),
            max_jobs=int(env_dict.get("MAX_JOBS", "10")),
            timeout_seconds=int(env_dict.get("TIMEOUT_SECONDS", "300")),
            schema_version=env_dict.get("SCHEMA_VERSION", "1.0"),
            api_url=env_dict.get("API_URL", "http://localhost:5001"),
        )
