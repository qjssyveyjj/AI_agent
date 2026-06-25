from fastapi import APIRouter
from pydantic import BaseModel

from app.security.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str = ""


@router.post("/login")
async def login(req: LoginRequest) -> dict:
    """
    演示用登录：签发 JWT。
    生产环境请替换为对接企业统一认证 / LDAP 的校验逻辑。
    """
    token = create_access_token(subject=req.username)
    return {"access_token": token, "token_type": "bearer"}
