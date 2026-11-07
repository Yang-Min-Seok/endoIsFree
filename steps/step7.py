import re
import time

from common.application_completion import (
    has_application_completion_message,
)
from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext
from playwright.sync_api import Dialog

APPLICATION_SUMMARY_SELECTOR = "table.table.sp-block-table"
APPLICATION_SELECT_SELECTOR = "#apply"
APPLICATION_BUTTON_SELECTOR = "#btn-go"
EXPECTED_HEADERS = ("分類", "公園", "施設", "利用日", "時間", "利用面数")
SUBMISSION_CONFIRMATION_MESSAGE = "抽選申込処理を行います。よろしいですか？"
SITE_COMMUNICATION_ERROR_MESSAGE = "データ通信を正しく行うことができませんでした"
APPLICATION_CATEGORY = "テニス（人工芝）"
COURT_COUNT = "1面"
SUMMARY_CELL_LABELS = ("分類：", "公園：", "施設：", "利用日：", "利用時間：", "利用面数：")
APPLICATION_ACTION_DELAY_SECONDS = 5


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _read_application_summary(context: ExecutionContext) -> tuple[str, ...]:
    context.page.wait_for_function(
        """({selector, expectedHeaders}) => {
            return Array.from(document.querySelectorAll(selector)).some(table => {
                const headers = Array.from(table.querySelectorAll("thead th"))
                    .map(header => header.textContent.replace(/\\s/g, ""));
                return JSON.stringify(headers) === JSON.stringify(expectedHeaders)
                    && table.querySelectorAll("tbody tr").length === 1;
            });
        }""",
        arg={
            "selector": APPLICATION_SUMMARY_SELECTOR,
            "expectedHeaders": list(EXPECTED_HEADERS),
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )

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


def _expected_application_values(
    context: ExecutionContext,
) -> tuple[str, ...]:
    start_time = context.config.start_times[
        context.application_round - 1
        if context.config.activity_hours == 4
        else 0
    ]
    return (
        APPLICATION_CATEGORY,
        context.config.park,
        context.config.facility,
        f"{context.config.month}月{context.config.day}日",
        f"{start_time:02d}時00分～{start_time + 2:02d}時00分",
        COURT_COUNT,
    )


def _validate_application_summary(
    context: ExecutionContext,
    summary: tuple[str, ...],
) -> None:
    mismatches = []
    for label, header, expected, actual in zip(
        SUMMARY_CELL_LABELS,
        EXPECTED_HEADERS,
        _expected_application_values(context),
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


def _handle_submission_dialog(
    dialog: Dialog,
    dialog_events: list[tuple[str, str]],
    context: ExecutionContext,
) -> None:
    message = dialog.message
    dialog_events.append((dialog.type, message))
    expected_message = _normalize_text(SUBMISSION_CONFIRMATION_MESSAGE)
    if (
        dialog.type == "alert"
        and SITE_COMMUNICATION_ERROR_MESSAGE in message
    ):
        context.workflow_state.site_communication_error = True
        dialog.accept()
        return
    if (
        dialog.type == "confirm"
        and _normalize_text(message) == expected_message
    ):
        if context.workflow_state.site_communication_error:
            dialog.dismiss()
        else:
            context.workflow_state.step7_confirmation_accepted = True
            dialog.accept()
    else:
        dialog.dismiss()


def run(context: ExecutionContext) -> None:
    context.workflow_state.current_process = "申込み回と開始時刻の設定を確認"
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
        "step7 called! Processing application %d/%d for account %d/%d.",
        context.application_round,
        context.application_round_count,
        context.user_index,
        context.user_count,
    )
    context.workflow_state.current_process = "サイトに表示された申込み内容を読み取る"
    summary = _read_application_summary(context)
    context.logger.info(
        "Application summary shown by the site: %s.",
        dict(zip(EXPECTED_HEADERS, summary)),
    )
    context.workflow_state.current_process = "サイトの申込み内容と設定を照合"
    _validate_application_summary(context, summary)
    context.logger.info("Application summary matches the configured request.")

    context.workflow_state.current_process = "申込み番号の選択肢を待つ"
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
    context.workflow_state.current_process = "選択した申込み番号を確認"
    selected_value = application_select.input_value()
    if selected_value != expected_option_value:
        raise RuntimeError(
            f"Expected {expected_option_label!r} to be selected, "
            f"but selected value is {selected_value!r}."
        )

    context.logger.info(
        "Waiting %d seconds after selecting the application number before "
        "clicking the final application button.",
        APPLICATION_ACTION_DELAY_SECONDS,
    )
    context.workflow_state.current_process = "申込みボタンをクリックする前に待機"
    time.sleep(APPLICATION_ACTION_DELAY_SECONDS)
    context.logger.info(
        "Wait complete. Clicking the final application button for %s.",
        expected_option_label,
    )
    context.workflow_state.current_process = "申込みボタンを押す準備"
    application_button = context.page.locator(APPLICATION_BUTTON_SELECTOR)
    application_button.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    dialog_events: list[tuple[str, str]] = []

    def dialog_handler(dialog: Dialog) -> None:
        _handle_submission_dialog(dialog, dialog_events, context)

    context.page.on("dialog", dialog_handler)
    try:
        context.workflow_state.current_process = (
            "申込みボタンを押してサイト確認ダイアログを処理"
        )
        with context.page.expect_navigation(
            wait_until="domcontentloaded",
            timeout=SITE_ACTION_TIMEOUT_MS,
        ) as navigation:
            application_button.click(timeout=SITE_ACTION_TIMEOUT_MS)

        context.workflow_state.current_process = "申込み後の遷移先を確認"
        response = navigation.value
        response_status = response.status if response is not None else None
        if response_status is not None and response_status >= 400:
            raise RuntimeError(
                "Application submission returned an unsuccessful HTTP status: "
                f"{response_status} ({context.page.url})."
            )
        context.page.wait_for_function(
            "() => document.readyState !== 'loading' "
            "&& document.body !== null "
            "&& document.body.innerText.trim().length > 0",
            timeout=SITE_ACTION_TIMEOUT_MS,
        )

        if has_application_completion_message(context.page):
            context.workflow_state.application_success_confirmed = True
            context.logger.info(
                "The application completion message appeared directly after "
                "step7 for account %d/%d, application %d/%d; page: %s.",
                context.user_index,
                context.user_count,
                context.application_round,
                context.application_round_count,
                context.page.url,
            )
            return

        if context.workflow_state.site_communication_error:
            raise RuntimeError(
                "The site displayed a communication error before the final "
                "confirmation was accepted."
            )

        if (
            len(dialog_events) != 1
            or dialog_events[0][0] != "confirm"
            or _normalize_text(dialog_events[0][1])
            != _normalize_text(SUBMISSION_CONFIRMATION_MESSAGE)
        ):
            raise RuntimeError(
                "The expected final application confirmation dialog was not "
                "accepted, or an unexpected dialog appeared. "
                f"Observed dialogs: {dialog_events!r}."
            )
        context.logger.info(
            "Accepted the step7 confirmation dialog. The final confirmation "
            "page will be handed off to the user in step8."
        )

        context.workflow_state.current_process = "最終確認ページへの遷移を確認"
        context.logger.info(
            "Step7 is ready for manual final confirmation for account %d/%d, "
            "application %d/%d; page: %s (HTTP %s).",
            context.user_index,
            context.user_count,
            context.application_round,
            context.application_round_count,
            context.page.url,
            response_status if response_status is not None else "no response",
        )
    finally:
        context.page.remove_listener("dialog", dialog_handler)
