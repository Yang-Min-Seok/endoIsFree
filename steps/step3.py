import time

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext

LOTTERY_MENU_SELECTOR = (
    'a.nav-link.dropdown-toggle[data-toggle="modal"][data-target="#modal-menus"]'
)
LOTTERY_APPLICATION_LINK_SELECTOR = (
    'a[href="javascript:doAction(document.form1, gLotWOpeLotSearchAction);"]'
)
LOTTERY_ACTION_DELAY_SECONDS = 5


def run(context: ExecutionContext) -> None:
    context.logger.info(
        "step3 called! Opening the lottery menu for account %d/%d.",
        context.user_index,
        context.user_count,
    )
    context.logger.info(
        "Waiting %d seconds before clicking the lottery navigation.",
        LOTTERY_ACTION_DELAY_SECONDS,
    )
    time.sleep(LOTTERY_ACTION_DELAY_SECONDS)
    context.logger.info("Wait complete. Clicking the lottery navigation.")
    context.page.locator(LOTTERY_MENU_SELECTOR).filter(has_text="抽選").click(
        timeout=SITE_ACTION_TIMEOUT_MS
    )

    application_link = context.page.locator(LOTTERY_APPLICATION_LINK_SELECTOR)
    application_link.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)

    context.logger.info(
        "Waiting %d seconds before clicking the lottery application link.",
        LOTTERY_ACTION_DELAY_SECONDS,
    )
    time.sleep(LOTTERY_ACTION_DELAY_SECONDS)
    context.logger.info("Wait complete. Clicking the lottery application link.")
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        application_link.click()

    response = navigation.value
    if response is not None and response.status >= 400:
        raise RuntimeError(
            "Lottery application page returned an unsuccessful HTTP status: "
            f"{response.status} ({context.page.url})."
        )

    context.page.wait_for_function(
        "() => document.readyState !== 'loading' "
        "&& document.body !== null "
        "&& document.body.innerText.trim().length > 0",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Lottery application page rendered successfully: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
