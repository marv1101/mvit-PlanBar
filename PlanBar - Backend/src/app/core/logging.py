import logging

from pythonjsonlogger import jsonlogger

TEXT_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def configure_logging(log_format: str = "TEXT") -> None:
    if log_format.upper() == "JSON":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logging.basicConfig(level=logging.INFO, handlers=[handler])
    else:
        logging.basicConfig(
            format=TEXT_FORMAT,
            level=logging.INFO,
        )
