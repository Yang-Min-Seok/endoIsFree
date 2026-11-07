import re

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

APPLICATION_SUMMARY_SELECTOR = "table.table.sp-block-table"
APPLICATION_SELECT_SELECTOR = "#apply"
APPLICATION_BUTTON_SELECTOR = "#btn-go"
EXPECTED_HEADERS = ("分類", "公園", "施設", "利用日", "時間", "利用面数")
CELL_LABELS = ("分類：", "公園：", "施設：", "利用日：", "利用時間：", "利用面数：")
APPLICATION_CATEGORY = "テニス（人工芝）"
COURT_COUNT = "1面"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _expected_time_label(context: ExecutionContext) -> str:
    start_time = context.config.start_times[
        context.application_round - 1
        if context.config.activity_hours == 4
        else 0
    ]
    return f"{start_time:02d}時00分～{start_time + 2:02d}時00分"


def _expected_summary_values(context: ExecutionContext) -> tuple[str, ...]:
    return (
        APPLICATION_CATEGORY,
        context.config.park,
        context.config.facility,
        f"{context.config.month}月{context.config.day}日",
        _expected_time_label(context),
        COURT_COUNT,
    )


def _read_application_summary(context: ExecutionContext) -> tuple[str, ...]:
    try:
        context.page.wait_for_function(
            """({selector, expectedHeaders, cellLabels, expectedValues}) => {
            return Array.from(document.querySelectorAll(selector)).some(table => {
                const headers = Array.from(table.querySelectorAll("thead th"))
                    .map(header => header.textContent.replace(/\\s/g, ""));
                if (JSON.stringify(headers) !== JSON.stringify(expectedHeaders)) {
                    return false;
                }
                const rows = table.querySelectorAll("tbody tr");
                if (rows.length !== 1) return false;
                const cells = Array.from(rows[0].querySelectorAll("td"));
                if (cells.length !== expectedValues.length) return false;
                return cells.every((cell, index) => {
                    let actual = cell.textContent.replace(/\\s/g, "");
                    const label = cellLabels[index];
                    if (actual.startsWith(label)) {
                        actual = actual.slice(label.length);
                    }
                    return index === 3
                        ? actual.includes(expectedValues[index])
                        : actual === expectedValues[index];
                });
            });
            }""",
            arg={
                "selector": APPLICATION_SUMMARY_SELECTOR,
                "expectedHeaders": list(EXPECTED_HEADERS),
                "cellLabels": list(CELL_LABELS),
                "expectedValues": [
                    _normalize_text(value)
                    for value in _expected_summary_values(context)
                ],
            },
            timeout=SITE_ACTION_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            "The application summary did not update to match the configured "
            "request before the timeout. No application was submitted."
        ) from error

    tables = context.page.locator(APPLICATION_SUMMARY_SELECTOR)
    matching_tables = []
    for table_index in range(tables.count()):
        table = tables.nth(table_index)
        headers = tuple(
            _normalize_text(header)
            for header in table.locator("thead th").all_text_contents()
        )
        if headers == EXPECTED_HEADERS:
            matching_tables.append(table)

    if len(matching_tables) != 1:
        raise RuntimeError(
            "Expected exactly one application summary table, "
            f"but found {len(matching_tables)}."
        )

    rows = matching_tables[0].locator("tbody tr")
    if rows.count() != 1:
        raise RuntimeError(
            "Expected exactly one application summary row, "
            f"but found {rows.count()}."
        )

    cells = rows.nth(0).locator("td")
    if cells.count() != len(EXPECTED_HEADERS):
        raise RuntimeError(
            "The application summary row has an unexpected number of cells: "
            f"{cells.count()}."
        )

    values: list[str] = []
    for cell_index in range(cells.count()):
        value = cells.nth(cell_index).text_content()
        if value is None:
            raise RuntimeError(
                f"Application summary cell {cell_index + 1} has no text."
            )
        values.append(_normalize_text(value))
    return tuple(values)


def _validate_application_summary(
    context: ExecutionContext,
    summary: tuple[str, ...],
) -> None:
    expected_values = _expected_summary_values(context)
    mismatches = []
    for label, header, expected, actual in zip(
        CELL_LABELS,
        EXPECTED_HEADERS,
        expected_values,
        summary,
    ):
        if actual.startswith(label):
            actual = actual[len(label):]
        if header == "利用日":
            matches = expected in actual
        else:
            matches = actual == _normalize_text(expected)
        if not matches:
            mismatches.append(
                f"{header}: expected {expected!r}, found {actual!r}"
            )

    if mismatches:
        raise RuntimeError(
            "Application summary does not match the configured request: "
            + "; ".join(mismatches)
        )


def run(context: ExecutionContext) -> None:
    if not 1 <= context.application_round <= context.application_round_count:
        raise ValueError(
            f"Application round must be between 1 and "
            f"{context.application_round_count}."
        )
    if context.application_round not in (1, 2):
        raise ValueError("Application round must be 1 or 2.")
    if (
        context.config.activity_hours == 4
        and context.application_round > len(context.config.start_times)
    ):
        raise ValueError(
            "The application round does not have a corresponding configured "
            "start time."
        )

    context.logger.info(
        "step7 called! Verifying application %d/%d for account %d/%d.",
        context.application_round,
        context.application_round_count,
        context.user_index,
        context.user_count,
    )
    summary = _read_application_summary(context)
    _validate_application_summary(context, summary)
    context.logger.info("Application summary matches the configured request.")

    application_select = context.page.locator(APPLICATION_SELECT_SELECTOR)
    application_select.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    expected_option_value = f"{context.application_round}-1"
    expected_option_label = f"申込み{context.application_round}件目"
    context.page.wait_for_function(
        """({selector, value, label}) => {
            const select = document.querySelector(selector);
            return select
                && !select.disabled
                && Array.from(select.options).some(
                    option => option.value === value
                        && option.textContent.trim() === label
                );
        }""",
        arg={
            "selector": APPLICATION_SELECT_SELECTOR,
            "value": expected_option_value,
            "label": expected_option_label,
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    application_select.select_option(
        value=expected_option_value,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    selected_value = application_select.input_value()
    if selected_value != expected_option_value:
        raise RuntimeError(
            f"Expected {expected_option_label!r} to be selected, "
            f"but selected value is {selected_value!r}."
        )

    application_button = context.page.locator(APPLICATION_BUTTON_SELECTOR)
    application_button.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.workflow_state.final_submission_started = True
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        application_button.click(timeout=SITE_ACTION_TIMEOUT_MS)

    response = navigation.value
    if response is not None and response.status >= 400:
        raise RuntimeError(
            "Application submission returned an unsuccessful HTTP status: "
            f"{response.status} ({context.page.url})."
        )
    context.page.wait_for_function(
        "() => document.readyState !== 'loading' "
        "&& document.body !== null "
        "&& document.body.innerText.trim().length > 0",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Application submitted for account %d/%d, application %d/%d; "
        "destination document loaded: %s (HTTP %s).",
        context.user_index,
        context.user_count,
        context.application_round,
        context.application_round_count,
        context.page.url,
        response.status if response is not None else "no response",
    )
