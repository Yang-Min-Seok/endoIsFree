import logging
import subprocess
import sys
from pathlib import Path


def play_page_loaded_sound(logger: logging.Logger) -> None:
    sound_file = Path(__file__).resolve().parents[1] / "sounds" / "step8.wav"

    try:
        if sys.platform == "win32":
            import winsound

            try:
                winsound.PlaySound(
                    str(sound_file),
                    winsound.SND_FILENAME | winsound.SND_ASYNC,
                )
            except RuntimeError as error:
                logger.warning(
                    "Could not play the custom reminder sound; using the "
                    "Windows system sound instead: %s",
                    error,
                )
                try:
                    winsound.PlaySound(
                        "SystemExclamation",
                        winsound.SND_ALIAS | winsound.SND_ASYNC,
                    )
                except RuntimeError:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        elif sys.platform == "darwin":
            subprocess.Popen(
                ["afplay", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
