"""
Development runner with auto-reload functionality.

Watches for file changes and automatically restarts the bot.
"""

import asyncio
import logging
import signal
import subprocess
import sys
from pathlib import Path

try:
    from watchfiles import awatch
except ImportError:
    print("Error: watchfiles is not installed. Install it with: uv sync --extra dev")
    sys.exit(1)

logger = logging.getLogger(__name__)


async def run_bot() -> subprocess.Popen:
    """
    Run the bot in a subprocess.

    Returns:
        Process object for the running bot
    """
    logger.info("Starting bot process...")
    process = subprocess.Popen(
        [sys.executable, "-m", "ds_discord_bot"],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    return process


async def main() -> None:
    """Main development runner with auto-reload."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Get the source directory to watch
    src_dir = Path(__file__).parent.parent.parent / "src"
    logger.info(f"Watching for changes in: {src_dir}")

    process: subprocess.Popen | None = None
    watch_task: asyncio.Task | None = None

    def cleanup_process() -> None:
        """Cleanup the bot process."""
        nonlocal process
        if process and process.poll() is None:
            logger.info("Stopping bot process...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't terminate, forcing kill...")
                process.kill()
                process.wait()
            process = None

    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        """Handle shutdown signals."""
        if not shutdown_event.is_set():
            logger.info("Received shutdown signal, cleaning up...")
            shutdown_event.set()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    else:
        # Windows doesn't support add_signal_handler
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

    try:
        # Start the bot initially
        process = await run_bot()

        # Watch for file changes
        async def watch_changes() -> None:
            nonlocal process
            try:
                async for changes in awatch(src_dir):
                    if shutdown_event.is_set():
                        break
                    if changes:
                        logger.info(f"Detected {len(changes)} file change(s), restarting bot...")
                        cleanup_process()
                        # Small delay to ensure files are fully written
                        await asyncio.sleep(0.5)
                        if not shutdown_event.is_set():
                            process = await run_bot()
            except asyncio.CancelledError:
                logger.debug("Watch task cancelled")
                raise

        # Start watching for changes
        watch_task = asyncio.create_task(watch_changes())

        # Wait for shutdown signal
        await shutdown_event.wait()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Cancel the watch task
        if watch_task and not watch_task.done():
            watch_task.cancel()
            try:
                await watch_task
            except asyncio.CancelledError:
                pass

        # Cleanup the bot process
        cleanup_process()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
