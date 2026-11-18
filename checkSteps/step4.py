from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import CheckExecutionContext, LotteryResultRecord

NO_RESULTS_TEXT = "該当する抽選はありません。"
UNCONFIRMED_WINNING_RESULTS_CAPTION = "確認されていない当選結果"
WINNING_RESULT_TABLE_SELECTOR = "table.table.sp-block-table"
WINNING_RESULT_HEADERS = (
    "公園・施設",
    "利用日",
    "利用時間",
    "利用料金",
    "確認",
)
WINNING_RESULT_CELL_LABELS = (
    "公園・施設：",
    "利用日：",
    "時刻：",
    "利用料金：",
)
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


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_header(value: str) -> str:
    return "".join(value.split())


def _read_winning_results(
    context: CheckExecutionContext,
) -> list[LotteryResultRecord]:
    context.page.wait_for_function(
        """({selector, captionText, expectedHeaders, expectedCellLabels}) => {
            return Array.from(document.querySelectorAll(selector)).some(table => {
                const caption = table.querySelector("caption");
                const headers = Array.from(table.querySelectorAll("thead th"))
                    .map(header => header.textContent.replace(/\\s/g, ""));
                const rows = Array.from(table.querySelectorAll("tbody tr"));
                return caption?.textContent.trim() === captionText
                    && JSON.stringify(headers) === JSON.stringify(expectedHeaders)
                    && rows.length > 0
                    && rows.every(row => {
                        const cells = Array.from(row.querySelectorAll("td"));
                        return cells.length === expectedHeaders.length
                            && expectedCellLabels.every((label, index) =>
                                cells[index].textContent.includes(label)
                            );
                    });
            });
        }""",
        arg={
            "selector": WINNING_RESULT_TABLE_SELECTOR,
            "captionText": UNCONFIRMED_WINNING_RESULTS_CAPTION,
            "expectedHeaders": list(WINNING_RESULT_HEADERS),
            "expectedCellLabels": list(WINNING_RESULT_CELL_LABELS),
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )

    tables = context.page.locator(WINNING_RESULT_TABLE_SELECTOR)
    matching_tables = []
    for table_index in range(tables.count()):
        table = tables.nth(table_index)
        captions = table.locator("caption").all_text_contents()
        headers = tuple(
            _normalize_header(header)
            for header in table.locator("thead th").all_text_contents()
        )
        if (
            tuple(_normalize_text(caption) for caption in captions)
            == (UNCONFIRMED_WINNING_RESULTS_CAPTION,)
            and headers == WINNING_RESULT_HEADERS
        ):
            matching_tables.append(table)

    if len(matching_tables) != 1:
        raise RuntimeError(
            "Expected exactly one unconfirmed-winning-results table, "
            f"but found {len(matching_tables)}."
        )

    rows = matching_tables[0].locator("tbody tr")
    if rows.count() == 0:
        raise RuntimeError("The winning-results table has no rows.")

    records: list[LotteryResultRecord] = []
    for row_index in range(rows.count()):
        cells = rows.nth(row_index).locator("td")
        if cells.count() != len(WINNING_RESULT_HEADERS):
            raise RuntimeError(
                f"Winning-result row {row_index + 1} has {cells.count()} "
                f"cells; expected {len(WINNING_RESULT_HEADERS)}."
            )

        values = []
        for index, label in enumerate(WINNING_RESULT_CELL_LABELS):
            cell_text = cells.nth(index).text_content()
            if cell_text is None:
                raise RuntimeError(
                    f"Winning-result cell {index + 1} has no text."
                )
            value = _normalize_text(cell_text)
            if not value.startswith(label):
                raise RuntimeError(
                    f"Expected winning-result cell to start with {label!r}, "
                    f"but found {value!r}."
                )
            value = value[len(label):].strip()
            if not value:
                raise RuntimeError(
                    f"Winning-result cell {index + 1} is empty."
                )
            values.append(value)

        records.append(
            LotteryResultRecord(
                user_number=context.user.user_number,
                result_type="当選",
                park_facility=values[0],
                use_date=values[1],
                use_time=values[2],
                fee=values[3],
            )
        )
    return records


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
        winning_results = _read_winning_results(context)
        context.check_state.lottery_results.extend(winning_results)
        context.workflow_state.current_process = "当選結果情報を記録"
        context.logger.info(
            "Collected %d winning result(s) for account %d/%d.",
            len(winning_results),
            context.user_index,
            context.user_count,
        )
        for result in winning_results:
            context.logger.info(
                "当選結果情報 | 利用者番号: %s | 公園・施設: %s | "
                "利用日: %s | 利用時間: %s | 利用料金: %s",
                result.user_number,
                result.park_facility,
                result.use_date,
                result.use_time,
                result.fee,
            )
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
