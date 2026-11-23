"""Chrome lifecycle for scans."""

import asyncio
import contextlib
import os
import shutil
import tempfile
from collections.abc import AsyncIterator

import nodriver as uc

from common.config import Configuration
from common.exceptions import CustomException, ErrorCode
from common.logger import logger

# TODO: Add headless mode
CHROME_ARGUMENTS = ["--disable-gpu", "--window-size=1920,1080", "--mute-audio"]
EXIT_TIMEOUT_IN_SECONDS = 10
PROFILE_REMOVAL_ATTEMPTS = 5
PROFILE_REMOVAL_INTERVAL_IN_SECONDS = 1


@contextlib.asynccontextmanager
async def open_browser() -> AsyncIterator[uc.Browser]:
    """Start Chrome with a temporary profile, then stop it and delete the profile.

    nodriver deletes its own profiles only when Python exits, so a bot that runs for days would
    leave one behind for every scan.

    Usage:
        async with open_browser() as browser:
            tab = await browser.get(url)

    Raises:
        CustomException: If Chrome cannot be started
    """
    profile_dir = tempfile.mkdtemp(prefix="yad2-chrome-")
    try:
        browser = await _start(profile_dir)
        try:
            yield browser
        finally:
            await _stop(browser)
    finally:
        await _remove_profile(profile_dir)


async def _start(profile_dir: str) -> uc.Browser:
    try:
        browser = await uc.start(
            browser_args=CHROME_ARGUMENTS,
            user_data_dir=profile_dir,
            sandbox=Configuration.Browser.SANDBOX,
        )
    except Exception as err:
        raise CustomException(
            message=f"Failed to start browser: {err}",
            error_code=ErrorCode.BROWSER_START_FAILED,
        ) from err
    logger.info("Browser started")
    return browser


async def _stop(browser: uc.Browser) -> None:
    """Stop Chrome and wait for it to exit, so that its profile can be deleted."""
    process = browser._process  # stop() clears it
    browser.stop()
    if process is None:
        return
    try:
        await asyncio.wait_for(process.wait(), EXIT_TIMEOUT_IN_SECONDS)
    except TimeoutError:
        logger.warning("Browser did not exit in time, killing it")
        process.kill()
        await process.wait()


async def _remove_profile(profile_dir: str) -> None:
    """Delete the profile. Chrome's child processes may still write to it for a moment."""
    for _ in range(PROFILE_REMOVAL_ATTEMPTS):
        await asyncio.to_thread(shutil.rmtree, profile_dir, ignore_errors=True)
        if not os.path.exists(profile_dir):
            return
        await asyncio.sleep(PROFILE_REMOVAL_INTERVAL_IN_SECONDS)
    logger.warning("Failed to delete the browser profile", profile_dir=profile_dir)
