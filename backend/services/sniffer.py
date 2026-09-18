def detect_mime_type(file_bytes: bytes) -> str:
    """Detect actual MIME type using binary signatures / magic bytes."""
    header = file_bytes[:16]

    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return "image/png"
    if header.startswith(b'\xff\xd8\xff'):
        return "image/jpeg"
    if header.startswith(b'RIFF') and file_bytes[8:12] == b'WEBP':
        return "image/webp"
    if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
        return "image/gif"
    if header.startswith(b'BM'):
        return "image/bmp"
    if header.startswith(b'%PDF'):
        return "application/pdf"

    if b'\x00' in file_bytes[:1024]:
        return "application/octet-stream"

    try:
        file_bytes.decode('utf-8')
        return "text/plain"
    except UnicodeDecodeError:
        return "application/octet-stream"