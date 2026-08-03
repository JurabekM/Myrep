import logging
import sys

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        ),
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # Audit logger is kept separate so it can later be routed to a dedicated,
    # tamper-evident sink without touching general app logs.
    audit_logger = logging.getLogger("dehqon.audit")
    audit_logger.setLevel(logging.INFO)


def audit(action: str, actor: str, detail: str = "") -> None:
    logging.getLogger("dehqon.audit").info("action=%s actor=%s detail=%s", action, actor, detail)
