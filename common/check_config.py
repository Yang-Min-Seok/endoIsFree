import json
from dataclasses import dataclass, field
from pathlib import Path

from common.config import UserAccount, load_user_accounts


@dataclass(frozen=True)
class CheckConfig:
    users: tuple[UserAccount, ...] = field(repr=False)


def load_check_config(config_path: Path) -> CheckConfig:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}. "
            "Create it with endoCustom/checkCustomizer.html."
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Configuration file contains invalid JSON: {config_path} "
            f"(line {error.lineno}, column {error.colno})."
        ) from error

    if not isinstance(config, dict):
        raise ValueError("Configuration must contain a users list.")

    return CheckConfig(users=load_user_accounts(config.get("users")))
