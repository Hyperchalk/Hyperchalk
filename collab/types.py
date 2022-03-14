from typing import TypedDict


class ExcalidrawBinaryFile(TypedDict, total=False):
    id: str
    created: int # unix time stamp
    dataURL: str
    mimeType: str

ALLOWED_IMAGE_MIME_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
}
