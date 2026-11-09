import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Optional


def start_user_action_reminder(
    logger: logging.Logger,
) -> Optional[Callable[[], None]]:
    sound_file = Path(__file__).resolve().parents[1] / "sounds" / "step8.wav"

    if sys.platform == "win32":
        try:
            import winsound
        except ImportError as error:
            logger.warning("Could not import the Windows sound player: %s", error)
            sys.stdout.write("\a")
            sys.stdout.flush()
            return None

        try:
            if not sound_file.is_file():
                raise RuntimeError(f"Sound file does not exist: {sound_file}")
            winsound.PlaySound(
                str(sound_file),
                winsound.SND_FILENAME
                | winsound.SND_ASYNC
                | winsound.SND_LOOP,
            )
        except RuntimeError as error:
            logger.warning(
                "Could not loop the custom reminder sound; using the "
                "Windows system sound instead: %s",
                error,
            )
            try:
                winsound.PlaySound(
                    "SystemExclamation",
                    winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_LOOP,
                )
            except RuntimeError as fallback_error:
                logger.warning(
                    "Could not start the Windows system reminder sound: %s",
                    fallback_error,
                )
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                return None

        def stop_windows_sound() -> None:
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError as error:
                logger.warning("Could not stop the reminder sound: %s", error)

        logger.info("Started looping the user-action reminder sound.")
        return stop_windows_sound

    if sys.platform == "darwin":
        if not sound_file.is_file():
            logger.warning("Reminder sound file does not exist: %s", sound_file)
            sys.stdout.write("\a")
            sys.stdout.flush()
            return None

        stop_event = threading.Event()
        process_lock = threading.Lock()
        try:
            process = subprocess.Popen(
                ["afplay", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            logger.warning("Could not start the reminder sound: %s", error)
            sys.stdout.write("\a")
            sys.stdout.flush()
            return None
        current_process = process

        def repeat_playback() -> None:
            nonlocal current_process, process
            while True:
                return_code = process.wait()
                if stop_event.is_set():
                    return
                if return_code != 0:
                    logger.warning(
                        "The reminder sound player exited with status %d.",
                        return_code,
                    )
                    return
                try:
                    next_process = subprocess.Popen(
                        ["afplay", str(sound_file)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except OSError as error:
                    logger.warning(
                        "Could not restart the reminder sound: %s",
                        error,
                    )
                    return
                with process_lock:
                    if stop_event.is_set():
                        next_process.terminate()
                        return
                    current_process = next_process
                    process = next_process

        playback_thread = threading.Thread(
            target=repeat_playback,
            name="step8-reminder-sound",
            daemon=True,
        )
        playback_thread.start()

        def stop_macos_sound() -> None:
            stop_event.set()
            with process_lock:
                process_to_stop = current_process
            try:
                if process_to_stop.poll() is None:
                    process_to_stop.terminate()
                    try:
                        process_to_stop.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process_to_stop.kill()
                        process_to_stop.wait()
            except OSError as error:
                logger.warning("Could not stop the reminder sound: %s", error)
            playback_thread.join(timeout=5)

        logger.info("Started looping the user-action reminder sound.")
        return stop_macos_sound

    sys.stdout.write("\a")
    sys.stdout.flush()
    logger.info("Played the terminal bell reminder.")
    return None
