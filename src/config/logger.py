import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(log_path: Path, name: str = None) -> logging.Logger:
    """Unified logger setup. Configures root logger if name is None."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger

    # Use INFO as default, can be overridden by caller
    logger.setLevel(logging.INFO)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Standardized format: [TIME] [LEVEL] [MODULE] - MESSAGE
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(name)-30s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Rotating File Handler (5MB, 3 backups)
    fh = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 2. Console Handler
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger
