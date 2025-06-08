import pytest

from src.ds_discord_bot.extensions.utils.messages import send_large_message


@pytest.mark.asyncio
async def test_send_large_message_basic():
    message = "a" * 4000
    chunks = [chunk async for chunk in send_large_message(message)]
    assert len(chunks) == 2
    assert chunks[0] == "a" * 2000
    assert chunks[1] == "a" * 2000


@pytest.mark.asyncio
async def test_send_large_message_with_split_at():
    message = "a.b.c!d?e" * 1000
    chunks = [chunk async for chunk in send_large_message(message)]
    assert len(chunks) >= 1
    assert isinstance(chunks[0], str)
