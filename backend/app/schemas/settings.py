from pydantic import BaseModel, Field


class SettingValue(BaseModel):
    key: str = Field(min_length=1, max_length=128)
    value: str | None = None
    is_secret: bool = True


class SettingsUpdateRequest(BaseModel):
    settings: list[SettingValue]


class SettingRead(BaseModel):
    key: str
    value: str | None
    is_secret: bool
    configured: bool


class SettingsReadResponse(BaseModel):
    settings: list[SettingRead]

