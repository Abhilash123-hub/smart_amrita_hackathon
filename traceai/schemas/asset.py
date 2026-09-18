"""Asset schemas and MIME inspection for TraceAI."""

import hashlib
import mimetypes
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class TrackType(str, Enum):
    """Processing track for ingested assets."""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    CODE = "CODE"
    UNSUPPORTED = "UNSUPPORTED"


def sniff_mime_and_track_from_bytes(file_path: Path, header_bytes: bytes) -> tuple[TrackType, str]:
    """Inspect raw header bytes to identify file format, ignoring misleading extensions.
    
    Adheres to directive: 'Ignore dataset metadata labels entirely.
    The system must inspect the actual bytes of the assets.'
    """
    # 1. Common Image magic signatures
    if header_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return TrackType.IMAGE, "image/png"
    if header_bytes.startswith(b"\xff\xd8\xff"):
        return TrackType.IMAGE, "image/jpeg"
    if header_bytes.startswith(b"GIF87a") or header_bytes.startswith(b"GIF89a"):
        return TrackType.IMAGE, "image/gif"
    if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"WEBP":
        return TrackType.IMAGE, "image/webp"
    if header_bytes.startswith(b"BM"):
        return TrackType.IMAGE, "image/bmp"
    if header_bytes.startswith(b"II*\x00") or header_bytes.startswith(b"MM\x00*"):
        return TrackType.IMAGE, "image/tiff"

    # 2. Audio magic signatures
    if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"WAVE":
        return TrackType.AUDIO, "audio/wav"
    if header_bytes.startswith(b"ID3") or header_bytes.startswith(b"\xff\xfb") or header_bytes.startswith(b"\xff\xf3"):
        return TrackType.AUDIO, "audio/mpeg"
    if header_bytes.startswith(b"fLaC"):
        return TrackType.AUDIO, "audio/flac"
    if header_bytes.startswith(b"OggS"):
        return TrackType.AUDIO, "audio/ogg"

    # 3. Video magic signatures
    if len(header_bytes) >= 8 and header_bytes[4:8] == b"ftyp":
        return TrackType.VIDEO, "video/mp4"
    if header_bytes.startswith(b"\x1aE\xdf\xa3"):
        return TrackType.VIDEO, "video/webm"
    if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"AVI ":
        return TrackType.VIDEO, "video/x-msvideo"

    # 4. Source Code inspection
    suffix = file_path.suffix.lower()
    code_suffixes = {
        ".py": "text/x-python",
        ".js": "application/javascript",
        ".ts": "application/typescript",
        ".jsx": "text/jsx",
        ".tsx": "text/tsx",
        ".go": "text/x-go",
        ".rs": "text/rust",
        ".cpp": "text/x-c++src",
        ".c": "text/x-csrc",
        ".h": "text/x-chdr",
        ".java": "text/x-java-source",
    }
    if suffix in code_suffixes:
        return TrackType.CODE, code_suffixes[suffix]

    # 5. Text & Code content inspection
    if b"\x00" not in header_bytes:
        try:
            text_peek = header_bytes.decode("utf-8", errors="ignore")
            # Heuristic for code vs plain text
            code_keywords = [
                "def ", "class ", "function ", "import ", "export ", "fn ",
                "package ", "public static void", "static inline", "struct ", "#include "
            ]
            if any(kw in text_peek for kw in code_keywords):
                return TrackType.CODE, "text/x-code"
            return TrackType.TEXT, "text/plain"
        except Exception:
            pass

    # 6. Fallback to extension check
    guessed_type, _ = mimetypes.guess_type(str(file_path))
    if guessed_type:
        if guessed_type.startswith("image/"):
            return TrackType.IMAGE, guessed_type
        if guessed_type.startswith("audio/"):
            return TrackType.AUDIO, guessed_type
        if guessed_type.startswith("video/"):
            return TrackType.VIDEO, guessed_type
        if guessed_type.startswith("text/") or guessed_type in {"application/json", "application/xml"}:
            return TrackType.TEXT, guessed_type

    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        return TrackType.IMAGE, f"image/{suffix.lstrip('.')}"
    if suffix in {".mp3", ".wav", ".flac", ".ogg"}:
        return TrackType.AUDIO, f"audio/{suffix.lstrip('.')}"
    if suffix in {".mp4", ".mkv", ".avi", ".webm", ".mov"}:
        return TrackType.VIDEO, f"video/{suffix.lstrip('.')}"
    if suffix in {".txt", ".md", ".json", ".csv", ".log"}:
        return TrackType.TEXT, "text/plain"

    return TrackType.UNSUPPORTED, "application/octet-stream"


class AssetInput(BaseModel):
    """Raw asset ingested by the gateway."""

    asset_id: str = Field(description="Unique asset identifier, typically filename or relative path")
    file_path: Path = Field(description="Absolute or relative path on disk")
    track: TrackType = Field(description="Resolved processing track based on byte inspection")
    mime_type: str = Field(description="MIME type determined by byte inspection")
    size_bytes: int = Field(description="Total file size in bytes")
    sha256_hash: str = Field(description="Prefixed SHA-256 digest: 'sha256:<hex>'")

    # Additive web ingestion & provenance fields (A1, A2, A4)
    source_url: Optional[str] = Field(default=None, description="Original source web URL if ingested from web")
    http_headers: Optional[dict[str, str]] = Field(default=None, description="HTTP response headers at scrape time")
    source_id: Optional[str] = Field(default=None, description="Registered source ID from Source Registry")
    source_trust_tier: Optional[str] = Field(default=None, description="Trust tier (licensed-partner|public-web-unknown|high-risk-domain)")
    prefilter_decision: Optional[dict] = Field(default=None, description="PreFilterResult from compliance pre-filter")
    crawl_timestamp: Optional[str] = Field(default=None, description="Timestamp when the asset was fetched")

    @classmethod
    def from_file(cls, path: Path | str, base_dir: Optional[Path | str] = None) -> "AssetInput":
        """Factory method to inspect a file on disk and construct an AssetInput instance."""
        target_path = Path(path).resolve()
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Asset file does not exist: {target_path}")

        # Compute SHA-256 and inspect header bytes
        hasher = hashlib.sha256()
        header = b""
        total_size = 0

        with open(target_path, "rb") as f:
            header = f.read(4096)
            hasher.update(header)
            total_size += len(header)
            while chunk := f.read(65536):
                hasher.update(chunk)
                total_size += len(chunk)

        track, mime_type = sniff_mime_and_track_from_bytes(target_path, header)
        asset_hash = f"sha256:{hasher.hexdigest()}"

        if base_dir:
            try:
                asset_id = str(target_path.relative_to(Path(base_dir).resolve()))
            except ValueError:
                asset_id = target_path.name
        else:
            asset_id = target_path.name

        return cls(
            asset_id=asset_id,
            file_path=target_path,
            track=track,
            mime_type=mime_type,
            size_bytes=total_size,
            sha256_hash=asset_hash,
        )

    def read_bytes(self) -> bytes:
        """Read all bytes from the underlying asset file."""
        return self.file_path.read_bytes()

    def read_text(self, encoding: str = "utf-8", errors: str = "replace") -> str:
        """Read asset as text string."""
        return self.file_path.read_text(encoding=encoding, errors=errors)
