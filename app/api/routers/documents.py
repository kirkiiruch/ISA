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
    summary="Upload document for background indexing",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    settings: Settings = Depends(get_app_settings),
):
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported media type: '{ext}'. Supported formats are: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB",
        )

    try:
        doc = await ingestion_service.create_document(filename=filename, content=content)
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate document: a document with identical content already exists.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Add background processing task
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
    summary="Get list of documents",
)
async def list_documents(
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
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
    summary="Get document details by ID",
)
async def get_document(
    document_id: str,
    doc_repo: DocumentRepository = Depends(get_document_repository),
):
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{document_id}' not found",
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
    summary="Delete document and all associated chunks",
)
async def delete_document(
    document_id: str,
    doc_repo: DocumentRepository = Depends(get_document_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
):
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id '{document_id}' not found",
        )

    await chunk_repo.delete_by_document_id(document_id)
    await doc_repo.delete(document_id)

    return MessageResponse(message=f"Document '{document_id}' and all associated chunks deleted successfully.")
