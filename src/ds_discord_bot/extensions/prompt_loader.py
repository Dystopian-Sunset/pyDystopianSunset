"""
Contextual prompt loader for loading and caching prompt modules.
"""

import logging
from pathlib import Path

import aiofiles
import aiofiles.os

logger = logging.getLogger(__name__)


class ContextualPromptLoader:
    """Loads prompt modules from filesystem with caching."""

    def __init__(self, base_path: Path):
        """
        Initialize the prompt loader.

        Args:
            base_path: Base path to the prompts directory
        """
        self.base_path = base_path
        self._cache: dict[str, str] = {}

    async def _load_file(self, file_path: Path) -> str:
        """
        Load a file's contents asynchronously.

        Args:
            file_path: Path to the file to load

        Returns:
            File contents as string
        """
        if not await aiofiles.os.path.isfile(file_path):
            logger.warning(f"Prompt file not found: {file_path}")
            return ""

        async with aiofiles.open(file_path) as f:
            content = await f.read()

        return content.strip()

    async def load_module(self, module_name: str) -> str:
        """
        Load a single prompt module, with caching.

        Args:
            module_name: Name of the module (without .md extension)

        Returns:
            Module content as string
        """
        if module_name in self._cache:
            logger.debug(f"Using cached prompt module: {module_name}")
            return self._cache[module_name]

        module_path = self.base_path / "modules" / f"{module_name}.md"
        content = await self._load_file(module_path)

        if content:
            self._cache[module_name] = content
            logger.info(f"Loaded prompt module: {module_name} ({len(content)} chars)")
        else:
            logger.warning(f"Empty or missing prompt module: {module_name}")

        return content

    async def load_modules(self, module_names: set[str]) -> list[str]:
        """
        Load multiple modules in order.

        Args:
            module_names: Set of module names to load

        Returns:
            List of module contents in load order
        """
        # Always load core first
        core_modules = ["core_identity", "formatting_guidelines", "content_guidelines"]
        other_modules = sorted(module_names - set(core_modules))

        prompts = []
        for module in core_modules + other_modules:
            if module in module_names:
                content = await self.load_module(module)
                if content:
                    prompts.append(content)

        return prompts

    def clear_cache(self) -> None:
        """Clear the module cache."""
        self._cache.clear()
        logger.debug("Prompt module cache cleared")
