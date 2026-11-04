from pathlib import Path

from common.browser import open_browser
from common.config import load_config
from common.context import ExecutionContext
from common.logging_config import configure_logging
from steps import step0, step1, step2, step3, step4, step5, step6, step7


def main() -> None:
    project_root = Path(__file__).resolve().parent
    logger = configure_logging(project_root)
    if not step0.ask_for_confirmation(logger):
        return

    config = load_config(project_root / "endoCustom" / "endoCustom.json")

    steps = (
        step1.run,
        step2.run,
        step3.run,
        step4.run,
        step5.run,
        step6.run,
        step7.run,
    )
    logger.info(
        "Launching browser in %s mode.",
        "visible" if config.show_browser else "background",
    )
    with open_browser(headless=not config.show_browser) as browser:
        for user_index, user in enumerate(config.users, start=1):
            logger.info(
                "Starting workflow for account %d/%d.",
                user_index,
                len(config.users),
            )
            browser_context = browser.new_context()
            try:
                context = ExecutionContext(
                    project_root=project_root,
                    logger=logger,
                    page=browser_context.new_page(),
                    user=user,
                    user_index=user_index,
                    user_count=len(config.users),
                    config=config,
                )
                for run_step in steps:
                    run_step(context)
            finally:
                browser_context.close()


if __name__ == "__main__":
    main()
