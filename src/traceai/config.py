"""Configuration settings and default thresholds for TraceAI Gateway (T0.3)."""

from pathlib import Path
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewayConfig(BaseSettings):
    """TraceAI Gateway operational configuration with TRACEAI_ env prefix."""

    model_config = SettingsConfigDict(
        env_prefix="TRACEAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Text Track thresholds
    text_recall_top_k: int = Field(
        default=5,
        description="Top-K candidates to retrieve from Bi-Encoder FAISS index"
    )
    text_cross_encoder_threshold: float = Field(
        default=0.85,
        validation_alias=AliasChoices(
            "TRACEAI_TEXT_BLOCK_THRESHOLD",
            "TRACEAI_TEXT_CROSS_ENCODER_THRESHOLD",
            "text_cross_encoder_threshold",
            "text_block_threshold",
        ),
        description="Cross-encoder pairwise similarity threshold (default: 0.85)"
    )
    text_bi_encoder_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )
    text_cross_encoder_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # Image Track thresholds
    image_phash_hamming_threshold: int = Field(
        default=8,
        description="pHash Hamming distance threshold for Stage 1 filter (default: 8)"
    )
    image_clip_cosine_threshold: float = Field(
        default=0.90,
        validation_alias=AliasChoices(
            "TRACEAI_IMAGE_BLOCK_THRESHOLD",
            "TRACEAI_IMAGE_CLIP_COSINE_THRESHOLD",
            "image_clip_cosine_threshold",
            "image_block_threshold",
        ),
        description="CLIP embedding cosine similarity threshold (default: 0.90)"
    )
    image_clip_model: str = Field(
        default="openai/clip-vit-base-patch32"
    )

    # Cryptography settings
    rsa_key_bits: int = Field(default=2048, description="RSA key size in bits")
    hash_algorithm: str = Field(default="SHA-256")
    signature_scheme: str = Field(default="RSASSA-PSS")

    # Storage and paths
    storage_root: str = Field(default="./data")
    evidence_locker_root: str = Field(default="./data/evidence")

    # Supported file extensions
    text_extensions: set[str] = Field(
        default_factory=lambda: {".txt", ".md", ".csv", ".json", ".text"}
    )
    image_extensions: set[str] = Field(
        default_factory=lambda: {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
    )


DEFAULT_CONFIG = GatewayConfig()
