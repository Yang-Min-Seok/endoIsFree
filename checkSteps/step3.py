import time

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import CommonExecutionContext

LOTTERY_MENU_SELECTOR = (
    "a.nav-link.dropdown-toggle.m-auto.d-table-cell.align-middle"
    '[data-toggle="modal"][data-target="#modal-menus"]'
)
LOTTERY_RESULTS_LINK_SELECTOR = (
    'a[href="javascript:doAction(document.form1, '
    'gLotWTransLotElectListAction);"]'
)
LOTTERY_ACTION_DELAY_SECONDS = 5


def run(context: CommonExecutionContext) -> None:
    context.workflow_state.current_process = "抽選メニューを開く前の待機"
    context.logger.info(
        "step3 called! Opening the lottery results for account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.logger.info(
        "Waiting %d seconds before clicking the lottery navigation.",
        LOTTERY_ACTION_DELAY_SECONDS,
    )
    time.sleep(LOTTERY_ACTION_DELAY_SECONDS)
    context.logger.info("Wait complete. Clicking the lottery navigation.")

    context.workflow_state.current_process = "抽選メニューを選択"
    context.page.locator(LOTTERY_MENU_SELECTOR).filter(has_text="抽選").click(
        timeout=SITE_ACTION_TIMEOUT_MS
    )

    context.workflow_state.current_process = "抽選結果リンクの表示を待つ"
    results_link = context.page.locator(LOTTERY_RESULTS_LINK_SELECTOR)
    results_link.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)

    context.logger.info(
        "Waiting %d seconds before clicking the lottery results link.",
        LOTTERY_ACTION_DELAY_SECONDS,
    )
    context.workflow_state.current_process = "抽選結果リンクのクリック前に待機"
    time.sleep(LOTTERY_ACTION_DELAY_SECONDS)
    context.logger.info("Wait complete. Clicking the lottery results link.")

    context.workflow_state.current_process = "抽選結果ページへ移動"
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        results_link.click(timeout=SITE_ACTION_TIMEOUT_MS)

    response = navigation.value
    if response is not None and response.status >= 400:
        raise RuntimeError(
            "Lottery results page returned an unsuccessful HTTP status: "
            f"{response.status} ({context.page.url})."
        )

    context.page.wait_for_function(
        "() => document.readyState !== 'loading' "
        "&& document.body !== null "
        "&& document.body.innerText.trim().length > 0",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.workflow_state.current_process = "抽選結果ページの表示を確認"
    context.logger.info(
        "Lottery results page rendered successfully: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
