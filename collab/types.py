from typing import Optional

from ninja import Schema


class ExcalidrawBinaryFile(Schema):
    id: str
    created: int # unix time stamp
    dataURL: str
    mimeType: str
    filePath: Optional[str]


ALLOWED_IMAGE_MIME_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
}
