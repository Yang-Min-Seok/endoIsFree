from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext


def run(context: ExecutionContext) -> None:
    context.logger.info(
        "step2 called! Logging in with account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.page.locator("#userId").fill(context.user.user_number)
    context.page.locator("#password").fill(context.user.password)

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
