import logging

from app.core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
