from common.browser import SITE_ACTION_TIMEOUT_MS
from common.context import CheckExecutionContext

COMPLETION_TITLE = "確認完了"
COMPLETION_MESSAGE = "当選の確認処理が完了しました。"


def run(context: CheckExecutionContext) -> None:
    context.workflow_state.current_process = "当選結果の確認完了を待つ"
    context.page.wait_for_function(
        """({titleText, messageText}) => {
            const titleFound = Array.from(
                document.querySelectorAll("h2.bottom-edge.session-title")
            ).some(element => element.textContent.includes(titleText));
            const messageFound = Array.from(
                document.querySelectorAll("div.mt-1")
            ).some(element => element.textContent.trim() === messageText);
            return titleFound && messageFound;
        }""",
        arg={
            "titleText": COMPLETION_TITLE,
            "messageText": COMPLETION_MESSAGE,
        },
        timeout=SITE_ACTION_TIMEOUT_MS,
    )
    context.check_state.winning_confirmation_completed = True
    context.check_state.account_workflow_complete = True
    context.workflow_state.current_process = "当選結果の確認完了を確認"
    context.logger.info(
        "Winning-result confirmation completed successfully for account "
        "%d/%d.",
        context.user_index,
        context.user_count,
    )
