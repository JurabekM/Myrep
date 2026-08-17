"""GridFS file storage with upload validation.

Validates size + extension + magic bytes before a single chunk is written,
so oversized or spoofed files never reach the database.
"""

from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from bson import ObjectId

from app.core.config import Settings
from app.core.exceptions import FileTooLargeError, NotFoundError, UnsupportedFileTypeError
from app.infrastructure.database.mongo import MongoManager

# Magic-byte signatures for the formats we accept. OOXML formats (docx/xlsx/
# pptx) share the ZIP signature; exact type is validated at parse time.
_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    # Plain-text formats have no signature.
    ".txt": (),
    ".csv": (),
}


@dataclass(frozen=True)
class StoredFile:
    file_id: str
    filename: str
    size: int
    content_type: str


class GridFSStorage:
    def __init__(self, mongo: MongoManager, settings: Settings):
        self._settings = settings
        self._bucket = AsyncIOMotorGridFSBucket(mongo.db)

    def _validate(self, filename: str, data: bytes) -> str:
        max_bytes = self._settings.max_upload_size_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise FileTooLargeError(
                f"Fayl {self._settings.max_upload_size_mb} MB dan katta bo'lmasligi kerak",
                details={"size": len(data), "max": max_bytes},
            )
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self._settings.allowed_upload_extensions:
            raise UnsupportedFileTypeError(
                "Fayl turi qo'llab-quvvatlanmaydi", details={"extension": ext}
            )
        signatures = _MAGIC_SIGNATURES.get(ext, ())
        if signatures and not any(data.startswith(sig) for sig in signatures):
            raise UnsupportedFileTypeError(
                "Fayl mazmuni kengaytmasiga mos emas", details={"extension": ext}
            )
        return ext

    async def upload(
        self, filename: str, data: bytes, content_type: str, *, user_id: str
    ) -> StoredFile:
        self._validate(filename, data)
        file_id = await self._bucket.upload_from_stream(
            filename,
            data,
            metadata={"content_type": content_type, "user_id": user_id},
        )
        return StoredFile(
            file_id=str(file_id), filename=filename, size=len(data), content_type=content_type
        )

    async def download(self, file_id: str) -> bytes:
        try:
            stream = await self._bucket.open_download_stream(ObjectId(file_id))
        except Exception as exc:  # gridfs raises NoFile; ObjectId raises InvalidId
            raise NotFoundError("Fayl topilmadi", details={"file_id": file_id}) from exc
        return await stream.read()

    async def delete(self, file_id: str) -> None:
        try:
            await self._bucket.delete(ObjectId(file_id))
        except Exception as exc:
            raise NotFoundError("Fayl topilmadi", details={"file_id": file_id}) from exc
