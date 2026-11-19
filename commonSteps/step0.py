import logging
import tkinter as tk
from tkinter import messagebox, simpledialog


QUESTION = "ミンソクくん、ツンデレ？"
EXPECTED_ANSWER = "真相は闇に葬ります"


def ask_for_confirmation(logger: logging.Logger) -> bool:
    root = tk.Tk()
    root.withdraw()
    try:
        answer = simpledialog.askstring(
            "endoIsFree",
            QUESTION,
            parent=root,
        )
        if answer is None:
            logger.info("step0 cancelled; workflow will not start.")
            return False

        if answer.strip() != EXPECTED_ANSWER:
            messagebox.showwarning(
                "endoIsFree",
                "回答が違います。処理は開始されません。",
                parent=root,
            )
            logger.info("step0 answer was incorrect; workflow will not start.")
            return False

        logger.info("step0 confirmed; starting workflow.")
        return True
    finally:
        root.destroy()
