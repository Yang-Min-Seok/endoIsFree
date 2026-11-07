from playwright.sync_api import Page

APPLICATION_SUCCESS_MESSAGE = "抽選の申込みが完了しました。"
APPLICATION_COMPLETION_MESSAGE_SELECTOR = "div.text-description"


def has_application_completion_message(page: Page) -> bool:
    completion_message = page.locator(
        APPLICATION_COMPLETION_MESSAGE_SELECTOR
    ).get_by_text(
        APPLICATION_SUCCESS_MESSAGE,
        exact=True,
    )
    return completion_message.is_visible()
