"""Configuration settings and default thresholds for TraceAI Gateway."""

from pathlib import Path
from pydantic import BaseModel, Field


class GatewayConfig(BaseModel):
    """TraceAI Gateway operational configuration."""
    
    # Text Track thresholds
    text_recall_top_k: int = Field(default=5, description="Top-K candidates to retrieve from Bi-Encoder FAISS index")
    text_cross_encoder_threshold: float = Field(default=0.85, description="Cross-encoder pairwise similarity threshold")
    text_bi_encoder_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    text_cross_encoder_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # Image Track thresholds
    image_phash_hamming_threshold: int = Field(default=5, description="pHash Hamming distance threshold for Stage 1 filter")
    image_clip_cosine_threshold: float = Field(default=0.90, description="CLIP embedding cosine similarity threshold")
    image_clip_model: str = Field(default="openai/clip-vit-base-patch32")

    # Cryptography settings
    rsa_key_bits: int = Field(default=2048, description="RSA key size in bits")
    hash_algorithm: str = Field(default="SHA-256")
    signature_scheme: str = Field(default="RSASSA-PSS")
    
    # Supported file extensions
    text_extensions: set[str] = Field(default_factory=lambda: {".txt", ".md", ".csv", ".json", ".text"})
    image_extensions: set[str] = Field(default_factory=lambda: {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"})


DEFAULT_CONFIG = GatewayConfig()
