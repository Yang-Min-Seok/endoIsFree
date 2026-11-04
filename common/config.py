import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class UserAccount:
    user_number: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class ApplicationConfig:
    users: tuple[UserAccount, ...] = field(repr=False)
    park: str
    facility: str
    month: int
    day: int
    activity_hours: int
    start_times: tuple[int, ...]
    show_browser: bool = True

    @property
    def start_time(self) -> int:
        return self.start_times[0]


def load_config(config_path: Path) -> ApplicationConfig:
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

    park = config.get("park")
    facility = config.get("facility")
    if not isinstance(park, str) or not park.strip():
        raise ValueError("Configuration must contain a park name.")
    if not isinstance(facility, str) or not facility.strip():
        raise ValueError("Configuration must contain a facility name.")

    month = config.get("month")
    day = config.get("day")
    activity_hours = config.get("activity_hours", 2)
    if (
        not isinstance(activity_hours, int)
        or isinstance(activity_hours, bool)
        or activity_hours not in (2, 4)
    ):
        raise ValueError("Configuration activity_hours must be 2 or 4.")

    if "start_times" in config:
        raw_start_times = config["start_times"]
        if not isinstance(raw_start_times, list):
            raise ValueError("Configuration start_times must be a list.")
    elif "start_time" in config and activity_hours == 2:
        raw_start_times = [config["start_time"]]
    else:
        raise ValueError("Configuration must contain start_times.")

    required_start_time_count = activity_hours // 2
    if len(raw_start_times) != required_start_time_count:
        raise ValueError(
            f"Configuration for {activity_hours} hours must contain "
            f"{required_start_time_count} start time(s)."
        )
    if any(
        not isinstance(start_time, int)
        or isinstance(start_time, bool)
        or start_time not in (9, 11, 13, 15, 17, 19)
        for start_time in raw_start_times
    ):
        raise ValueError("Start times must be selected from 9, 11, 13, 15, 17, 19.")
    if len(set(raw_start_times)) != len(raw_start_times):
        raise ValueError("Start times must be different from each other.")

    if not isinstance(month, int) or isinstance(month, bool) or not 1 <= month <= 12:
        raise ValueError("Configuration month must be an integer from 1 to 12.")
    if not isinstance(day, int) or isinstance(day, bool) or not 1 <= day <= 31:
        raise ValueError("Configuration day must be an integer from 1 to 31.")

    show_browser = config.get("show_browser", True)
    if not isinstance(show_browser, bool):
        raise ValueError("Configuration show_browser must be true or false.")

    return ApplicationConfig(
        users=tuple(accounts),
        park=park.strip(),
        facility=facility.strip(),
        month=month,
        day=day,
        activity_hours=activity_hours,
        start_times=tuple(raw_start_times),
        show_browser=show_browser,
    )
