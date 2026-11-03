import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class UserAccount:
    user_number: str
    password: str = field(repr=False)


def load_user_accounts(config_path: Path) -> tuple[UserAccount, ...]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}. "
            "Create it with endoCustom/customizer.html."
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Configuration file contains invalid JSON: {config_path} "
            f"(line {error.lineno}, column {error.colno})."
        ) from error

    if not isinstance(config, dict) or not isinstance(config.get("users"), list):
        raise ValueError("Configuration must contain a users list.")
    if not config["users"]:
        raise ValueError("Configuration must contain at least one user.")

    accounts: list[UserAccount] = []
    seen_user_numbers: set[str] = set()
    for index, record in enumerate(config["users"], start=1):
        if not isinstance(record, dict):
            raise ValueError(f"User record {index} must be an object.")

        user_number = record.get("user_number")
        password = record.get("password")
        if not isinstance(user_number, str) or not user_number.strip():
            raise ValueError(f"User record {index} has an empty or invalid user number.")
        if not isinstance(password, str) or not password:
            raise ValueError(f"User record {index} has an empty or invalid password.")
        if len(user_number.strip()) > 8:
            raise ValueError(f"User record {index} user number exceeds 8 characters.")
        if len(password) > 24:
            raise ValueError(f"User record {index} password exceeds 24 characters.")

        normalized_user_number = user_number.strip()
        if normalized_user_number in seen_user_numbers:
            raise ValueError(f"User record {index} duplicates an earlier user number.")

        seen_user_numbers.add(normalized_user_number)
        accounts.append(
            UserAccount(
                user_number=normalized_user_number,
                password=password,
            )
        )

    return tuple(accounts)
