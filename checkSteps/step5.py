from common.context import CheckExecutionContext
from checkSteps import step5_no_win, step5_winner


def run(context: CheckExecutionContext) -> None:
    has_winning_results = (
        context.check_state.has_unconfirmed_winning_results
    )
    if has_winning_results is None:
        raise RuntimeError(
            "Step5 cannot choose a branch before step4 determines the result."
        )

    if has_winning_results:
        step5_winner.run(context)
    else:
        step5_no_win.run(context)
        context.check_state.account_workflow_complete = True
