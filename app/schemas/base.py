from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )
class AuthInputSchema(BaseSchema):
    model_config = ConfigDict(
        str_strip_whitespace=False,
        extra="forbid",
    )