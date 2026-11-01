class ChunkingFailedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmbeddingFailedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsupportedFormatError(ChunkingFailedError):
    pass


class NoChunkStrategyError(ChunkingFailedError):
    pass
