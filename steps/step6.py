from typing import Optional

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext

USE_DATE_TABLE_SELECTOR = "#usedate-table"
NEXT_WEEK_BUTTON_SELECTOR = "#next-week"
APPLICATION_BUTTON_SELECTOR = "#btn-go"
MAX_WEEKS_TO_SEARCH = 52


def _week_dates(context: ExecutionContext) -> tuple[str, ...]:
    date_inputs = context.page.locator(
        f"{USE_DATE_TABLE_SELECTOR} thead input[name='selectUseYMD']"
    )
    dates: list[str] = []
    for index in range(date_inputs.count()):
        value = date_inputs.nth(index).get_attribute("value")
        if value is None or len(value) != 8 or not value.isdigit():
            raise RuntimeError(
                f"Unexpected date value in calendar column {index + 1}: {value!r}."
            )
        dates.append(value)
    if not dates:
        raise RuntimeError("The use-date table does not contain any date columns.")
    return tuple(dates)


def _find_target_date_column(
    context: ExecutionContext,
    previous_dates: Optional[tuple[str, ...]] = None,
) -> Optional[int]:
    dates = _week_dates(context)
    if previous_dates is not None and dates == previous_dates:
        return None

    for index, value in enumerate(dates):
        month = int(value[4:6])
        day = int(value[6:8])
        if month == context.config.month and day == context.config.day:
            return index
    return None


def _select_target_date_column(context: ExecutionContext) -> int:
    table = context.page.locator(USE_DATE_TABLE_SELECTOR)
    table.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)
    context.page.wait_for_function(
        """selector => {
            const table = document.querySelector(selector);
            return table
                && table.getClientRects().length > 0
                && table.querySelector("thead input[name='selectUseYMD']")
                && table.querySelector("tbody tr");
        }""",
        arg=USE_DATE_TABLE_SELECTOR,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )

    for week_number in range(MAX_WEEKS_TO_SEARCH + 1):
        target_column = _find_target_date_column(context)
        if target_column is not None:
            return target_column

        if week_number == MAX_WEEKS_TO_SEARCH:
            break

        next_week = context.page.locator(NEXT_WEEK_BUTTON_SELECTOR)
        next_week.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)
        if next_week.is_disabled():
            raise RuntimeError(
                f"Could not find {context.config.month}月{context.config.day}日: "
                "the next-week button is disabled."
            )

        previous_dates = _week_dates(context)
        next_week.click(timeout=SITE_ACTION_TIMEOUT_MS)
        context.page.wait_for_function(
            """({selector, previousDates}) => {
                const table = document.querySelector(selector);
                if (!table) return false;
                const currentDates = Array.from(
                    table.querySelectorAll("thead input[name='selectUseYMD']")
                ).map(input => input.value);
                return currentDates.length > 0
                    && JSON.stringify(currentDates) !== JSON.stringify(previousDates);
            }""",
            arg={
                "selector": USE_DATE_TABLE_SELECTOR,
                "previousDates": list(previous_dates),
            },
            timeout=SITE_ACTION_TIMEOUT_MS,
        )

    raise RuntimeError(
        f"Could not find {context.config.month}月{context.config.day}日 "
        f"within {MAX_WEEKS_TO_SEARCH} weeks."
    )


def _expected_time_label(start_time: int) -> str:
    return f"{start_time:02d}時00分～{start_time + 2:02d}時00分"


def run(context: ExecutionContext) -> None:
    if not 1 <= context.application_round <= context.application_round_count:
        raise ValueError(
            f"Application round must be between 1 and "
            f"{context.application_round_count}."
        )
    if (
        context.config.activity_hours == 4
        and context.application_round > len(context.config.start_times)
    ):
        raise ValueError(
            "The application round does not have a corresponding configured "
            "start time."
        )

    start_time = context.config.start_times[
        context.application_round - 1
        if context.config.activity_hours == 4
        else 0
    ]
    context.logger.info(
        "step6 called! Selecting %d:00 on %d月%d日 for account %d/%d, "
        "application %d/%d.",
        start_time,
        context.config.month,
        context.config.day,
        context.user_index,
        context.user_count,
        context.application_round,
        context.application_round_count,
    )

    date_column = _select_target_date_column(context)
    start_time_value = str(start_time * 100)
    rows = context.page.locator(
        f"{USE_DATE_TABLE_SELECTOR} tbody tr:"
        f"has(input[name='selectStime'][value='{start_time_value}'])"
    )
    row_count = rows.count()
    if row_count != 1:
        raise RuntimeError(
            f"Expected exactly one time row for {start_time}:00, "
            f"but found {row_count}."
        )

    target_cell = rows.locator("td").nth(date_column)
    target_cell.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)
    target_cell.click(timeout=SITE_ACTION_TIMEOUT_MS)

    expected_date_fragment = f"{context.config.month}月{context.config.day}日"
    expected_time = _expected_time_label(start_time)
    context.page.wait_for_function(
        """({dateFragment, expectedTime}) => {
            const date = document.querySelector("#selectDisplayUseYMD");
            const time = document.querySelector("#selectDisplayTime");
            return date
                && date.textContent.includes(dateFragment)
                && time
                && time.textContent.trim() === expectedTime;
        }""",
        arg={
            "dateFragment": expected_date_fragment,
            "expectedTime": expected_time,
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Selected %s at %s for application %d/%d.",
        expected_date_fragment,
        expected_time,
        context.application_round,
        context.application_round_count,
    )

    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        context.page.locator(APPLICATION_BUTTON_SELECTOR).click(
            timeout=SITE_ACTION_TIMEOUT_MS
        )

    response = navigation.value
    if response is not None and response.status >= 400:
        raise RuntimeError(
            "Application details page returned an unsuccessful HTTP status: "
            f"{response.status} ({context.page.url})."
        )
    context.page.wait_for_function(
        "() => document.readyState !== 'loading' "
        "&& document.body !== null "
        "&& document.body.innerText.trim().length > 0",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Application details page for step7 loaded: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
