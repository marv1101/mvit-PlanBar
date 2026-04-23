import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    database_url: str
    queue_table: str = "job_queue"
    callback_queue: str = "callback_queue"
    max_jobs: int = 10
    timeout_seconds: int = 300
    schema_version: str = "1.0"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = env or os.environ
        return cls(
            database_url=env.get("DATABASE_URL", "sqlite:///tito.db"),
            queue_table=env.get("QUEUE_TABLE", "job_queue"),
            callback_queue=env.get("CALLBACK_QUEUE", "callback_queue"),
            max_jobs=int(env.get("MAX_JOBS", "10")),
            timeout_seconds=int(env.get("TIMEOUT_SECONDS", "300")),
            schema_version=env.get("SCHEMA_VERSION", "1.0"),
        )
