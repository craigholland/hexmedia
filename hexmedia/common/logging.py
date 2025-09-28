# xvideo/common/logging.py
from __future__ import annotations

import logging


def get_logger(name: str = "uvicorn.error", level: int = logging.INFO) -> logging.Logger:
    """
    Return a logger that plays nice with Uvicorn if running under it.
    If no handlers are set, we add a basicConfig once.
    """
    logger = logging.getLogger(name)
    if not logging.getLogger().handlers and not logger.handlers:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.setLevel(level)
    return logger
