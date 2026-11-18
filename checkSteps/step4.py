from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import CheckExecutionContext

NO_RESULTS_TEXT = "該当する抽選はありません。"
UNCONFIRMED_WINNING_RESULTS_CAPTION = "確認されていない当選結果"
LOSING_APPLICATIONS_BUTTON_SELECTOR = "#lotconfbtn-go"
LOSING_APPLICATIONS_BUTTON_TEXT = "落選した申込みはこちら"
WINNING_RESULT_SELECT_LABEL_SELECTOR = (
    'label.btn.sp-upward-offset2-btn.checkboxbtn[for="checkelect0"]'
)
WINNING_RESULT_SELECT_LABEL_TEXT = "選択"
WINNING_RESULTS_CONFIRM_BUTTON_SELECTOR = "#btn-go"
WINNING_RESULTS_CONFIRM_BUTTON_TEXT = "確認"


def _has_exact_text(context: CheckExecutionContext, selector: str, text: str) -> bool:
    return any(
        value.strip() == text
        for value in context.page.locator(selector).all_text_contents()
    )


def run(context: CheckExecutionContext) -> None:
    context.workflow_state.current_process = "抽選結果の表示を待つ"
    context.logger.info(
        "step4 called! Checking lottery results for account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.page.wait_for_function(
        """({noResultsText, winningCaption}) => {
            const hasNoResults = Array.from(
                document.querySelectorAll("#text-area")
            ).some(element => element.textContent.trim() === noResultsText);
            const hasWinningResults = Array.from(
                document.querySelectorAll("caption")
            ).some(element => element.textContent.trim() === winningCaption);
            return hasNoResults || hasWinningResults;
        }""",
        arg={
            "noResultsText": NO_RESULTS_TEXT,
            "winningCaption": UNCONFIRMED_WINNING_RESULTS_CAPTION,
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )

    context.workflow_state.current_process = "当選結果の有無を判定"
    has_no_results = _has_exact_text(
        context,
        "#text-area",
        NO_RESULTS_TEXT,
    )
    has_winning_results = _has_exact_text(
        context,
        "caption",
        UNCONFIRMED_WINNING_RESULTS_CAPTION,
    )
    if has_no_results == has_winning_results:
        raise RuntimeError(
            "Could not uniquely determine the lottery result: "
            f"no-results marker={has_no_results}, "
            f"winning-results caption={has_winning_results}."
        )

    context.check_state.has_unconfirmed_winning_results = has_winning_results
    if has_winning_results:
        context.logger.info(
            "Unconfirmed winning results were found for account %d/%d. "
            "There may be up to two winning results.",
            context.user_index,
            context.user_count,
        )
        context.workflow_state.current_process = "当選結果の選択ラベルを待つ"
        winning_result_select_label = context.page.locator(
            WINNING_RESULT_SELECT_LABEL_SELECTOR
        ).filter(has_text=WINNING_RESULT_SELECT_LABEL_TEXT)
        winning_result_select_label.wait_for(
            state="visible",
            timeout=SITE_ACTION_TIMEOUT_MS,
        )
        context.workflow_state.current_process = "当選結果を選択"
        winning_result_select_label.click(timeout=SITE_ACTION_TIMEOUT_MS)
        context.workflow_state.current_process = "当選結果を選択済み"
        context.logger.info(
            "Selected a winning result for account %d/%d.",
            context.user_index,
            context.user_count,
        )
        context.workflow_state.current_process = "当選結果の確認ボタンを待つ"
        confirm_button = context.page.locator(
            WINNING_RESULTS_CONFIRM_BUTTON_SELECTOR
        ).filter(has_text=WINNING_RESULTS_CONFIRM_BUTTON_TEXT)
        confirm_button.wait_for(
            state="visible",
            timeout=SITE_ACTION_TIMEOUT_MS,
        )

        context.workflow_state.current_process = "当選結果を確認して次の画面へ移動"
        with context.page.expect_navigation(
            wait_until="domcontentloaded",
            timeout=SITE_ACTION_TIMEOUT_MS,
        ) as navigation:
            confirm_button.click(timeout=SITE_ACTION_TIMEOUT_MS)

        response = navigation.value
        if response is not None and response.status >= 400:
            raise RuntimeError(
                "Winning results confirmation page returned an unsuccessful "
                f"HTTP status: {response.status} ({context.page.url})."
            )

        context.page.wait_for_function(
            "() => document.readyState !== 'loading' "
            "&& document.body !== null "
            "&& document.body.innerText.trim().length > 0",
            timeout=SITE_ACTION_TIMEOUT_MS,
        )
        context.workflow_state.current_process = "当選結果確認後の画面表示を確認"
        context.logger.info(
            "Winning results confirmation page rendered successfully: %s "
            "(HTTP %s).",
            context.page.url,
            response.status if response is not None else "no response",
        )
        return

    context.logger.info(
        "No applicable lottery results were found for account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.workflow_state.current_process = "落選した申込み一覧ボタンの表示を待つ"
    losing_applications_button = context.page.locator(
        LOSING_APPLICATIONS_BUTTON_SELECTOR
    ).filter(has_text=LOSING_APPLICATIONS_BUTTON_TEXT)
    losing_applications_button.wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )

    context.workflow_state.current_process = "落選した申込み一覧へ移動"
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        losing_applications_button.click(timeout=SITE_ACTION_TIMEOUT_MS)

    response = navigation.value
    if response is not None and response.status >= 400:
        raise RuntimeError(
            "Losing applications page returned an unsuccessful HTTP status: "
            f"{response.status} ({context.page.url})."
        )

    context.page.wait_for_function(
        "() => document.readyState !== 'loading' "
        "&& document.body !== null "
        "&& document.body.innerText.trim().length > 0",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.workflow_state.current_process = "落選した申込み一覧の表示を確認"
    context.logger.info(
        "Losing applications page rendered successfully: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
