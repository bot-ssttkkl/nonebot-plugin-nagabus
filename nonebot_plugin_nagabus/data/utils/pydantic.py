from pydantic import BaseModel
from sqlalchemy import JSON, TypeDecorator


class PydanticModel(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, t_model: type[BaseModel], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t_model = t_model

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.dict()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.t_model.parse_obj(value)
