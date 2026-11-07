import logging
import subprocess
import sys


def play_page_loaded_sound(logger: logging.Logger) -> None:
    try:
        if sys.platform == "win32":
            import winsound

            try:
                winsound.PlaySound(
                    "SystemExclamation",
                    winsound.SND_ALIAS,
                )
            except RuntimeError:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        elif sys.platform == "darwin":
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        else:
            sys.stdout.write("\a")
            sys.stdout.flush()
    except (
        ImportError,
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        logger.warning(
            "Could not play the user-action reminder sound: %s",
            error,
        )
        return

    logger.info("Played the user-action reminder sound.")
