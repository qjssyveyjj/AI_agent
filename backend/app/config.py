from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 大模型服务
    llm_base_url: str = "http://localhost:8000/v1"
    llm_api_key: str = "sk-placeholder"
    llm_model: str = "Qwen3-VL-Plus"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.3

    # Agent 循环
    agent_max_steps: int = 5

    # 内部 API
    internal_api_base: str = "http://192.168.126.200/dev-api"
    internal_api_token: str = ""
    internal_api_timeout: int = 15

    # 会话与存储
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = ""
    session_ttl_seconds: int = 86400

    # 安全
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    auth_enabled: bool = False

    # 图片预处理
    image_max_edge: int = 1024
    image_jpeg_quality: int = 85

    # CORS
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
