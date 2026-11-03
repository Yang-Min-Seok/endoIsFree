import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecutionContext:
    project_root: Path
    logger: logging.Logger
