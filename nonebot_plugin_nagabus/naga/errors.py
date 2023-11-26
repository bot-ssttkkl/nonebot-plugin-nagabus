from collections.abc import Sequence


class NagaError(BaseException):
    ...


class InvalidTokenError(NagaError):
    ...


class OrderError(NagaError):
    ...


class InvalidGameError(NagaError):
    ...


class UnsupportedGameError(NagaError):
    ...


class InvalidKyokuHonbaError(NagaError):
    def __init__(self, available_kyoku_honba: Sequence[tuple[int, int]]):
        super().__init__()
        self.available_kyoku_honba = available_kyoku_honba
