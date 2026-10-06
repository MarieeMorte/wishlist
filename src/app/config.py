from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://wishlist:wishlist@localhost:5432/wishlist"
    wb_dest: int = -1257786
    wb_spp: int = 0
    wb_timeout: float = 10.0


settings = Settings()

