import re
from typing import Optional

from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import CheckExecutionContext, LotteryResultRecord

RESULT_TABLE_SELECTOR = "table.table.sp-block-table"
EXPECTED_HEADERS = (
    "状態",
    "予約番号",
    "公園・施設",
    "利用日",
    "利用時間",
    "利用料金",
)
CELL_LABELS = (
    "公園・施設：",
    "利用日：",
    "利用時間：",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _matching_result_table(context: CheckExecutionContext):
    tables = context.page.locator(RESULT_TABLE_SELECTOR)
    matching_tables = []
    for table_index in range(tables.count()):
        table = tables.nth(table_index)
        headers = tuple(
            _normalize_header(header)
            for header in table.locator("thead th").all_text_contents()
        )
        if headers == EXPECTED_HEADERS:
            matching_tables.append(table)

    if len(matching_tables) != 1:
        raise RuntimeError(
            "Expected exactly one losing-application result table, "
            f"but found {len(matching_tables)}."
        )
    return matching_tables[0]


def _cell_value(cell_text: str, label: Optional[str]) -> str:
    value = _normalize_text(cell_text)
    if label is not None:
        if not value.startswith(label):
            raise RuntimeError(
                f"Expected result cell to start with {label!r}, "
                f"but found {value!r}."
            )
        value = value[len(label):].strip()
    if not value:
        raise RuntimeError("A losing-application result cell is empty.")
    return value


def _read_losing_applications(
    context: CheckExecutionContext,
) -> list[LotteryResultRecord]:
    context.page.wait_for_function(
        """({selector, expectedHeaders, expectedCellLabels}) => {
            return Array.from(document.querySelectorAll(selector)).some(table => {
                const headers = Array.from(table.querySelectorAll("thead th"))
                    .map(header => header.textContent.replace(/\\s/g, ""));
                const rows = Array.from(table.querySelectorAll("tbody tr"));
                return JSON.stringify(headers) === JSON.stringify(expectedHeaders)
                    && rows.length > 0
                    && rows.every(row => {
                        const cells = Array.from(row.querySelectorAll("td"));
                        return cells.length === expectedHeaders.length
                            && cells.every((cell, index) => {
                                const text = cell.textContent.replace(/\\s/g, "");
                                if (index === 0) return text.includes("落選");
                                if (index === cells.length - 1) return text.length > 0;
                                return text.includes(expectedCellLabels[index]);
                            });
                    });
            });
        }""",
        arg={
            "selector": RESULT_TABLE_SELECTOR,
            "expectedHeaders": list(EXPECTED_HEADERS),
            "expectedCellLabels": [
                "",
                "予約番号：",
                "公園・施設：",
                "利用日：",
                "利用時間：",
                "",
            ],
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    table = _matching_result_table(context)
    rows = table.locator("tbody tr")
    if rows.count() == 0:
        raise RuntimeError("The losing-application result table has no rows.")

    records: list[LotteryResultRecord] = []
    for row_index in range(rows.count()):
        cells = rows.nth(row_index).locator("td")
        if cells.count() != len(EXPECTED_HEADERS):
            raise RuntimeError(
                f"Losing-application row {row_index + 1} has "
                f"{cells.count()} cells; expected {len(EXPECTED_HEADERS)}."
            )
        cell_values = []
        for index, label in enumerate(CELL_LABELS, start=2):
            cell_text = cells.nth(index).text_content()
            if cell_text is None:
                raise RuntimeError(
                    f"Losing-application cell {index + 1} has no text."
                )
            cell_values.append(_cell_value(cell_text, label))
        fee = cells.nth(5).text_content()
        if fee is None or not _normalize_text(fee):
            raise RuntimeError(
                f"Losing-application fee cell in row {row_index + 1} "
                "is empty."
            )
        records.append(
            LotteryResultRecord(
                user_number=context.user.user_number,
                result_type="落選",
                park_facility=cell_values[0],
                use_date=cell_values[1],
                use_time=cell_values[2],
                fee=_normalize_text(fee),
            )
        )
    return records


def run(context: CheckExecutionContext) -> None:
    context.workflow_state.current_process = "落選した申込み一覧を待つ"
    context.logger.info(
        "step5 no-win branch is called for account %d/%d.",
        context.user_index,
        context.user_count,
    )
    records = _read_losing_applications(context)
    context.check_state.lottery_results.extend(records)
    context.workflow_state.current_process = "落選した申込み情報を記録"
    context.logger.info(
        "Collected %d losing-application result(s) for account %d/%d.",
        len(records),
        context.user_index,
        context.user_count,
    )
    context.logger.info("========== 落選申込み情報 ==========")
    context.logger.info(
        "| 利用者番号 | 公園・施設 | 利用日 | 利用時間 | 利用料金 |"
    )
    context.logger.info("| --- | --- | --- | --- | --- |")
    for record in records:
        context.logger.info(
            "| %s | %s | %s | %s | %s |",
            record.user_number,
            record.park_facility,
            record.use_date,
            record.use_time,
            record.fee,
        )
    context.logger.info("====================================")
