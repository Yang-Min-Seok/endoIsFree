import logging
from pathlib import Path

from common.context import ExecutionContext
from common.logging_config import configure_logging
from steps import step1, step2, step3, step4, step5, step6, step7


def main() -> None:
    project_root = Path(__file__).resolve().parent
    logger = configure_logging(project_root)
    context = ExecutionContext(project_root=project_root, logger=logger)

    for run_step in (
        step1.run,
        step2.run,
        step3.run,
        step4.run,
        step5.run,
        step6.run,
        step7.run,
    ):
        run_step(context)


if __name__ == "__main__":
    main()
