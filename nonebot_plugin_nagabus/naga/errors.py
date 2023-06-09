from typing import Tuple, Sequence


class NagaError(BaseException):
    ...


class OrderError(NagaError):
    ...


class InvalidGameError(NagaError):
    ...


class UnsupportedGameError(NagaError):
    ...


class InvalidKyokuHonbaError(NagaError):
    def __init__(self, available_kyoku_honba: Sequence[Tuple[int, int]]):
        super().__init__()
        self.available_kyoku_honba = available_kyoku_honba
