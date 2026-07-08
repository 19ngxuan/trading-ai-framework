from pydantic import BaseModel, ConfigDict


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LoginRequest(CamelModel):
    username: str
    password: str


class LoginResponse(CamelModel):
    accessToken: str
    tokenType: str = "bearer"
    expiresInSeconds: int
    username: str


class AuthMeResponse(CamelModel):
    authEnabled: bool
    authenticated: bool
    username: str | None
