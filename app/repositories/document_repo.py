"""Репозиторій для роботи з колекцією документів у MongoDB."""

from typing import List, Optional
from pymongo.asynchronous.database import AsyncDatabase
from app.models.document import DocumentModel, DocumentStatus, get_utc_now


class DocumentRepository:
    """Клас доступу до документів компанії."""

    def __init__(self, db: AsyncDatabase):
        self.collection = db["documents"]

    async def create(self, doc: DocumentModel) -> DocumentModel:
        """Зберегти новий документ."""
        doc_dict = doc.model_dump()
        await self.collection.insert_one(doc_dict)
        return doc

    async def get_by_id(self, doc_id: str) -> Optional[DocumentModel]:
        """Знайти документ за його ID."""
        doc_dict = await self.collection.find_one({"id": doc_id}, {"_id": 0})
        if not doc_dict:
            return None
        return DocumentModel.model_validate(doc_dict)

    async def get_by_hash(self, content_hash: str) -> Optional[DocumentModel]:
        """Знайти документ за хешем вмісту."""
        doc_dict = await self.collection.find_one({"content_hash": content_hash}, {"_id": 0})
        if not doc_dict:
            return None
        return DocumentModel.model_validate(doc_dict)

    async def list_all(self) -> List[DocumentModel]:
        """Отримати всі документи від найновіших."""
        cursor = self.collection.find({}, {"_id": 0}).sort("created_at", -1)
        results = []
        async for doc_dict in cursor:
            results.append(DocumentModel.model_validate(doc_dict))
        return results

    async def update_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunks_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Оновити статус обробки та кількість чанків."""
        update_fields = {
            "status": status.value,
            "updated_at": get_utc_now(),
        }
        if chunks_count is not None:
            update_fields["chunks_count"] = chunks_count
        if error_message is not None:
            update_fields["error_message"] = error_message

        result = await self.collection.update_one(
            {"id": doc_id},
            {"$set": update_fields},
        )
        return result.modified_count > 0

    async def delete(self, doc_id: str) -> bool:
        """Видалити документ за його ID."""
        result = await self.collection.delete_one({"id": doc_id})
        return result.deleted_count > 0
