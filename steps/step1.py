from common.context import ExecutionContext


def run(context: ExecutionContext) -> None:
    context.logger.info("step1 called!")
