from common.context import ExecutionContext
from common.browser import SITE_ACTION_TIMEOUT_MS

TOP_PAGE_URL = "https://kouen.sports.metro.tokyo.lg.jp/web/"


def run(context: ExecutionContext) -> None:
    context.workflow_state.current_process = "予約サイトのトップページを開く"
    context.logger.info(
        "step1 called! Opening the reservation site for account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.page.goto(
        TOP_PAGE_URL,
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.workflow_state.current_process = "ログインページへ移動"
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        context.page.locator("#btn-login").click()

    context.workflow_state.current_process = "ログイン入力欄の表示を確認"
    context.page.locator("#userId").wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    response = navigation.value
    context.logger.info(
        "Login page is ready: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
