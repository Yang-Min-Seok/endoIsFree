from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext

LOTTERY_TABLE_SELECTOR = "table.table.sp-block-table.mt-3"
LOTTERY_CATEGORY = "テニス（人工芝）"


def run(context: ExecutionContext) -> None:
    context.workflow_state.current_process = "抽選分類一覧を待つ"
    context.logger.info(
        "step4 called! Selecting %s for account %d/%d.",
        LOTTERY_CATEGORY,
        context.user_index,
        context.user_count,
    )

    table = context.page.locator(LOTTERY_TABLE_SELECTOR)
    table.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)

    category_cells = table.locator("tbody td.sp-top").filter(
        has_text=LOTTERY_CATEGORY
    )
    context.workflow_state.current_process = "テニス（人工芝）の抽選枠を特定"
    matching_cells = [
        cell
        for cell in category_cells.all()
        if cell.inner_text().strip() == LOTTERY_CATEGORY
    ]
    if len(matching_cells) != 1:
        raise RuntimeError(
            f"Expected exactly one lottery row for {LOTTERY_CATEGORY}, "
            f"but found {len(matching_cells)}."
        )

    row = matching_cells[0].locator("xpath=ancestor::tr")
    context.workflow_state.current_process = "抽選受付中か確認"
    status_text = row.locator("td.status").inner_text().strip()
    if status_text != "受付中":
        raise RuntimeError(
            f"Lottery applications for {LOTTERY_CATEGORY} are not open "
            f"(current status: {status_text or 'unknown'})."
        )

    apply_button = row.locator("td.request button").filter(has_text="申込み")
    context.workflow_state.current_process = "抽選分類を選択して画面遷移"
    apply_button.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)
    with context.page.expect_navigation(
        wait_until="domcontentloaded",
        timeout=SITE_ACTION_TIMEOUT_MS,
    ) as navigation:
        apply_button.click(timeout=SITE_ACTION_TIMEOUT_MS)

    response = navigation.value
    if response is not None and response.status >= 400:
        raise RuntimeError(
            "Lottery category page returned an unsuccessful HTTP status: "
            f"{response.status} ({context.page.url})."
        )

    context.page.wait_for_function(
        "() => document.readyState !== 'loading' "
        "&& document.body !== null "
        "&& document.body.innerText.trim().length > 0",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.workflow_state.current_process = "公園選択欄の準備を確認"
    context.page.wait_for_load_state(
        "load",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.page.locator("#bname").wait_for(
        state="visible",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.page.wait_for_function(
        """() => {
            const parkSelect = document.querySelector("#bname");
            return parkSelect
                && !parkSelect.disabled
                && parkSelect.options.length > 0;
        }""",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Lottery category page and park selector are ready: %s (HTTP %s).",
        context.page.url,
        response.status if response is not None else "no response",
    )
