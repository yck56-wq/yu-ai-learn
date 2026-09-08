import ipaddress
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=512)

    @field_validator('code')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('code cannot be blank')
        return value.strip()


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)

    @field_validator('nickname')
    @classmethod
    def nickname_text(cls, value):
        if value is not None and any(ord(c) < 32 for c in value):
            raise ValueError('nickname contains control characters')
        return value

    @field_validator('avatar_url')
    @classmethod
    def public_avatar(cls, value):
        if not value:
            return value
        url = urlsplit(value)
        host = (url.hostname or '').lower().rstrip('.')
        if url.scheme != 'https' or not host or '.' not in host or url.username or url.password or any(c.isspace() for c in value):
            raise ValueError('avatar must use a public HTTPS URL')
        if host.endswith(('.localhost', '.local', '.internal')) or host == 'localhost':
            raise ValueError('local avatar is not supported')
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not address.is_global:
                raise ValueError('private avatar is not supported')
        return value

    @model_validator(mode='after')
    def supplied_fields(self):
        if not self.model_fields_set or any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError('supply nickname or avatar_url')
        return self
