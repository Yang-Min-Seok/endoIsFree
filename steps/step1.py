from common.context import ExecutionContext

TOP_PAGE_URL = "https://kouen.sports.metro.tokyo.lg.jp/web/"


def run(context: ExecutionContext) -> None:
    context.logger.info("step1 called! Opening the reservation site.")
    context.page.goto(TOP_PAGE_URL, wait_until="domcontentloaded")
    with context.page.expect_navigation(wait_until="load", timeout=60_000) as navigation:
        context.page.locator("#btn-login").click()

    response = navigation.value
    context.logger.info(
        "Login button clicked; destination page loaded: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
