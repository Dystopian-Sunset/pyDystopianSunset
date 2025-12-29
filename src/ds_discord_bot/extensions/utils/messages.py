from collections.abc import Iterable


async def send_large_message(
    message: str,
    chunk_length: int = 2000,
    split_at: set[str] | None = None,
) -> Iterable[str]:
    if split_at is None:
        split_at = {".", "!", "?"}
    """
    Splits a message into chunks of 2000 characters or less, preferring to split at sentence boundaries.
    """
    max_length = chunk_length
    start = 0
    message_length = len(message)

    while start < message_length:
        end = min(start + max_length, message_length)
        chunk = message[start:end]

        # Find each split point
        split_points = [chunk.rfind(punctuation) for punctuation in split_at]
        split_points = [point for point in split_points if point != -1]

        if split_points:
            # Try to split at the last sentence-ending punctuation within the chunk
            split_index = max(split_points)
            if split_index != -1 and end != message_length:
                # Split at the punctuation mark (include it)
                split_point = start + split_index + 1
            else:
                split_point = end
        else:
            split_point = end

        yield message[start:split_point].strip()
        start = split_point
