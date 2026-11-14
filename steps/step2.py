import time

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext

INPUT_ACTION_DELAY_SECONDS = 5


def run(context: ExecutionContext) -> None:
    context.workflow_state.current_process = "利用者番号を入力"
    context.logger.info(
        "step2 called! Logging in with account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.page.locator("#userId").fill(context.user.user_number)
    context.workflow_state.current_process = "利用者番号入力後の待機"
    context.logger.info(
        "User number entered. Waiting %d seconds before entering password.",
        INPUT_ACTION_DELAY_SECONDS,
    )
    time.sleep(INPUT_ACTION_DELAY_SECONDS)
    context.logger.info("Wait complete. Entering the password.")
    context.workflow_state.current_process = "パスワードを入力"
    context.page.locator("#password").fill(context.user.password)
    context.workflow_state.current_process = "パスワード入力後の待機"
    context.logger.info(
        "Password entered. Waiting %d seconds before submitting login.",
        INPUT_ACTION_DELAY_SECONDS,
    )
    time.sleep(INPUT_ACTION_DELAY_SECONDS)
    context.logger.info("Wait complete. Submitting login.")

    context.workflow_state.current_process = "ログインを送信して画面遷移を待つ"
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        context.page.locator("#btn-go").click()

    response = navigation.value
    context.logger.info(
        "Login submitted; destination document loaded: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
