import time

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import ExecutionContext

PARK_SELECT_SELECTOR = "#bname"
FACILITY_SELECT_SELECTOR = "#iname"
USE_DATE_TABLE_SELECTOR = "#usedate-table"
PARK_SELECTION_WAIT_SECONDS = 10


def _selected_label(context: ExecutionContext, selector: str) -> str:
    selected_label = context.page.locator(selector).evaluate(
        "select => select.selectedOptions[0]?.textContent?.trim() ?? ''"
    )
    return str(selected_label)


def run(context: ExecutionContext) -> None:
    context.logger.info(
        "step5 called! Selecting park and facility for account %d/%d.",
        context.user_index,
        context.user_count,
    )

    context.page.wait_for_load_state(
        "load",
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    park_select = context.page.locator(PARK_SELECT_SELECTOR)
    park_select.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)
    context.page.wait_for_function(
        """parkName => {
            const select = document.querySelector("#bname");
            return select
                && !select.disabled
                && Array.from(select.options).some(
                    option => option.textContent.trim() === parkName
                );
        }""",
        arg=context.config.park,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    park_select.select_option(
        label=context.config.park,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    selected_park = _selected_label(context, PARK_SELECT_SELECTOR)
    if selected_park != context.config.park:
        raise RuntimeError(
            f"Selected park does not match configuration: {selected_park!r}."
        )
    context.logger.info(
        "Selected park: %s. Waiting %d seconds before selecting the facility.",
        selected_park,
        PARK_SELECTION_WAIT_SECONDS,
    )
    time.sleep(PARK_SELECTION_WAIT_SECONDS)

    context.page.wait_for_function(
        """facilityName => {
            const select = document.querySelector("#iname");
            return select
                && !select.disabled
                && Array.from(select.options).some(
                    option => option.textContent.trim() === facilityName
                );
        }""",
        arg=context.config.facility,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    facility_select = context.page.locator(FACILITY_SELECT_SELECTOR)
    facility_select.select_option(
        label=context.config.facility,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    selected_facility = _selected_label(context, FACILITY_SELECT_SELECTOR)
    if selected_facility != context.config.facility:
        raise RuntimeError(
            "Selected facility does not match configuration: "
            f"{selected_facility!r}."
        )
    context.logger.info("Selected facility: %s.", selected_facility)

    table = context.page.locator(USE_DATE_TABLE_SELECTOR)
    table.wait_for(state="visible", timeout=SITE_ACTION_TIMEOUT_MS)
    context.page.wait_for_function(
        """tableSelector => {
            const table = document.querySelector(tableSelector);
            return table
                && table.getClientRects().length > 0
                && table.querySelector("thead th")
                && table.querySelector("tbody tr");
        }""",
        arg=USE_DATE_TABLE_SELECTOR,
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.logger.info(
        "Use-date table is ready for %s / %s (account %d/%d).",
        selected_park,
        selected_facility,
        context.user_index,
        context.user_count,
    )
