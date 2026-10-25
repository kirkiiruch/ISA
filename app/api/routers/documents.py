"""Роутер для завантаження, отримання списку та видалення документів."""

import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from app.api.dependencies import (
    get_document_repository,
    get_chunk_repository,
    get_ingestion_service,
    get_app_settings,
)
from app.core.config import Settings
from app.repositories.document_repo import DocumentRepository
from app.repositories.chunk_repo import ChunkRepository
from app.services.ingestion import IngestionService, SUPPORTED_EXTENSIONS
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentListItem,
    DocumentDetailResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadResponse,
    summary="Завантаження документа для фонової індексації",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_app_settings),
):
    """Прийняти документ на індексацію у фоновому режимі."""
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Непідтримуваний формат '{ext}'. Дозволені формати: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Розмір файлу перевищує ліміт {settings.MAX_FILE_SIZE_MB}MB",
        )

    try:
        doc = await ingestion_service.create_document(filename=filename, content=content)
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Файл із таким вмістом уже було завантажено раніше (дублікат).",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    background_tasks.add_task(
        ingestion_service.process_document_background,
        document_id=doc.id,
        filename=filename,
        content=content,
    )

    return DocumentUploadResponse(id=doc.id, status=doc.status)


@router.get(
    "",
    response_model=List[DocumentListItem],
    summary="Отримати список усіх документів",
)
async def list_documents(
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
    """Повернути список збережених документів."""
    docs = await doc_repo.list_all()
    return [
        DocumentListItem(
            id=d.id,
            filename=d.filename,
            status=d.status,
            chunks_count=d.chunks_count,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Отримати детальну інформацію про документ",
)
async def get_document(
    document_id: str,
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
    """Повернути деталі документа за його ідентифікатором."""
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Документ з ID '{document_id}' не знайдено",
        )
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        chunks_count=doc.chunks_count,
        file_size=doc.file_size,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Видалити документ та пов'язані чанки",
)
async def delete_document(
    document_id: str,
    doc_repo: DocumentRepository = Depends(get_document_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
):
    """Видалити документ разом із усіма його збереженими векторами."""
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Документ з ID '{document_id}' не знайдено",
        )

    await chunk_repo.delete_by_document_id(document_id)
    await doc_repo.delete(document_id)

    return MessageResponse(message=f"Document '{document_id}' deleted successfully.")
