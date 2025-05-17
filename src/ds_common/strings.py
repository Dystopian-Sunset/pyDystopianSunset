def ellipsize(text: str, max_length: int = 100) -> str:
    return (text[:max_length - 3] + '...') if len(text) > max_length else text