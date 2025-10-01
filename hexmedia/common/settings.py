# hexmedia/common/settings.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, AliasChoices, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from hexmedia.common.strings.splitters import csv_to_list




def _to_bool(v: str | bool | int | None, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    prefix: str = "/api"

    cors_allow_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    cors_allow_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    cors_allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False
    #
    # @field_validator("cors_allow_origins", "cors_allow_methods", "cors_allow_headers", mode="before")
    # @classmethod
    # def _split_csv(cls, v):
    #     return _csv_to_list(v)


class DBConfig(BaseModel):
    driver: str = "postgresql+psycopg"
    host: str = "localhost"
    port: int = 5432
    name: str = "hexmedia"
    user: str = "hexuser"
    password: str = "hexpass"
    schema_name: str = Field(default="hexmedia", alias="DB_SCHEMA")
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True
    pool_recycle: int = 1800

    # Optional single URL (if set, it takes precedence)
    url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    @computed_field  # type: ignore[misc]
    @property
    def effective_url(self) -> str:
        if self.url:
            return self.url
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class ConcurrencyConfig(BaseModel):
    max_scan_workers: int = 8
    hash_workers: int = 4
    ffprobe_workers: int = 4
    thread_queue_maxsize: int = 64
    cancel_on_exit: bool = True

    @field_validator("cancel_on_exit", mode="before")
    @classmethod
    def _boolify(cls, v):
        return _to_bool(v, default=True)


class FFProbeConfig(BaseModel):
    timeout_sec: int = 30
    log_level: str = "error"  # quiet|panic|fatal|error|warning|info|verbose|debug|trace
    bin: str = Field(default="/usr/bin/ffprobe", alias="FFPROBE_BIN")


class FeatureFlags(BaseModel):
    ingest_enabled: bool = True
    dup_detect_by_hash: bool = True
    write_phash: bool = False
    asset_autogen_thumbs: bool = False

    @field_validator("*", mode="before")
    @classmethod
    def _boolify(cls, v):
        return _to_bool(v)


class Settings(BaseSettings):
    # -------- App / Env --------
    app_name: str = "hexmedia"
    app_env: str = "development"  # development|test|staging|production
    log_level: str = "INFO"
    tz: str = "UTC"

    # -------- Docker user/group --------
    docker_uid: int = 1000
    docker_gid: int = 1000
    docker_shared_root: Path = Path("/mnt/shared")

    # -------- Paths & layout (host-side) --------
    data_root: Path = Path("/media/sf_common_shared/hexmedia")
    incoming_subdir: str = "incoming"
    media_subdir: str = "media"
    processed_subdir: str = "processed"
    temp_subdir: str = ".tmp"

    # Optional absolute overrides (leave empty to use DATA_ROOT + subdir)
    incoming_root_override: Optional[Path] = Field(default=None, alias="INCOMING_ROOT")
    media_root_override: Optional[Path] = Field(default=None, alias="MEDIA_ROOT")

    # -------- Identity / Naming rules --------
    bucket_name_length: int = 7
    item_name_length: int = 7
    hexmedia_bucket_max: int = 2000
    ingest_run_limit: int = Field(10, description="Default max files to plan/run per request")

    # -------- Allowed extensions --------
    video_exts: List[str] = Field(default_factory=lambda: ["mp4", "mov", "flv"])
    image_exts: List[str] = Field(default_factory=lambda: ["jpg", "jpeg", "png", "gif", "webp"])
    sidecar_exts: List[str] = Field(default_factory=lambda: ["vtx"])

    # @field_validator("video_exts", "image_exts", "sidecar_exts", mode="before")
    # @classmethod
    # def _split_csv(cls, v):
    #     return _csv_to_list(v)
    # This is moved to hexmedia.common.strings.splitter

    # -------- Sub-configs --------
    api: APIConfig = APIConfig()
    db: DBConfig = DBConfig()
    concurrency: ConcurrencyConfig = ConcurrencyConfig()
    ffprobe: FFProbeConfig = FFProbeConfig()
    features: FeatureFlags = FeatureFlags()

    # -------- Alembic / migrations --------
    alembic_script_location: str = "hexmedia/database/alembic"
    alembic_version_table_schema: str = "public"

    # -------- Observability / Security (stubs) --------
    enable_structured_logs: bool = True
    sentry_dsn: str = ""
    metrics_enabled: bool = False
    metrics_port: int = 9102
    jwt_secret: str = "dev-only-secret"
    jwt_algo: str = "HS256"

    # -------- Testcontainers / CI toggles --------
    use_testcontainers: bool = True
    test_db_image: str = "postgres:15-alpine"
    test_db_wait_timeout_sec: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------- Thumbnail imaging --------
    thumb_format: str = Field("png", description="Default thumbnail image format (png|jpg|jpeg|webp)")
    collage_format: str = Field("png", description="Default collage image format (png|jpg|jpeg|webp)")
    thumb_width: int = Field(960, ge=64, le=4096, description="Width of single-frame thumbnails")
    collage_tile_width: int = Field(400, ge=64, le=4096, description="Width of each tile in collage")
    upscale_policy: str = Field("if_smaller_than", description="never|if_smaller_than|always")

    MAX_THUMB_WORKERS: int = Field(8, ge=1, le=64, description="Upper bound for /thumb workers param")

    # ===== Derived paths =====
    @computed_field  # type: ignore[misc]
    @property
    def incoming_root(self) -> Path:
        if self.incoming_root_override:
            return Path(self.incoming_root_override)
        return self.data_root / self.incoming_subdir

    @computed_field  # type: ignore[misc]
    @property
    def media_root(self) -> Path:
        if self.media_root_override:
            return Path(self.media_root_override)
        return self.data_root / self.media_subdir

    @computed_field  # type: ignore[misc]
    @property
    def processed_root(self) -> Path:
        return self.data_root / self.processed_subdir

    @computed_field  # type: ignore[misc]
    @property
    def temp_root(self) -> Path:
        return self.data_root / self.temp_subdir

    # ===== Convenience: DB URL & schema =====
    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        return self.db.effective_url

    @computed_field  # type: ignore[misc]
    @property
    def db_schema(self) -> str:
        return self.db.schema_name


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Global settings accessor (cached). Use this everywhere you need config:
        from hexmedia.common.settings import get_settings
        cfg = get_settings()
    """
    s = Settings()  # pydantic_settings will read from .env automatically
    # Ensure derived directories exist in dev/test (optional):
    if s.app_env in ("development", "test"):
        for p in (s.data_root, s.incoming_root, s.media_root, s.processed_root, s.temp_root):
            p.mkdir(parents=True, exist_ok=True)
    return s
