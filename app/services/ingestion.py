import hashlib
import io
import logging
import os
from typing import List, Tuple, Optional
from pypdf import PdfReader
from app.ai.base import EmbeddingClient
from app.core.config import Settings
from app.models.document import DocumentModel, DocumentStatus, ChunkModel
from app.repositories.document_repo import DocumentRepository
from app.repositories.chunk_repo import ChunkRepository

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Splits text into chunks of given size with overlap.
    """
    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    if len(cleaned_text) <= chunk_size:
        return [cleaned_text]

    chunks = []
    start = 0
    stride = max(1, chunk_size - chunk_overlap)
    while start < len(cleaned_text):
        end = start + chunk_size
        chunk = cleaned_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned_text):
            break
        start += stride

    return chunks


def extract_text_and_pages(filename: str, content: bytes) -> List[Tuple[Optional[int], str]]:
    """
    Extracts text and page numbers from document content.
    Returns list of (page_number, text).
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        pages_text = []
        reader = PdfReader(io.BytesIO(content))
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append((page_idx + 1, text))
        return pages_text

    elif ext in {".txt", ".md"}:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
        return [(1, text)] if text.strip() else []

    else:
        raise ValueError(f"Unsupported file format: {ext}")


class IngestionService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        embedding_client: EmbeddingClient,
        settings: Settings,
    ):
        self.doc_repo = document_repo
        self.chunk_repo = chunk_repo
        self.embedding_client = embedding_client
        self.settings = settings

    def validate_file(self, filename: str, content_size: int):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {ext}")
        max_bytes = self.settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if content_size > max_bytes:
            raise ValueError(f"File size exceeds maximum allowed limit of {self.settings.MAX_FILE_SIZE_MB}MB")

    async def create_document(self, filename: str, content: bytes) -> DocumentModel:
        self.validate_file(filename, len(content))
        content_hash = calculate_sha256(content)

        existing = await self.doc_repo.get_by_hash(content_hash)
        if existing:
            raise FileExistsError(f"Duplicate document with hash {content_hash} already exists")

        doc = DocumentModel(
            filename=filename,
            content_hash=content_hash,
            file_size=len(content),
            status=DocumentStatus.PROCESSING,
        )
        return await self.doc_repo.create(doc)

    async def process_document_background(self, document_id: str, filename: str, content: bytes):
        """
        Background task: parsing -> chunking -> embedding -> storing.
        Updates document status to READY or FAILED.
        """
        try:
            pages = extract_text_and_pages(filename, content)
            chunks: List[ChunkModel] = []
            chunk_index = 0

            for page_num, page_text in pages:
                text_splits = split_text_into_chunks(
                    page_text,
                    chunk_size=self.settings.CHUNK_SIZE,
                    chunk_overlap=self.settings.CHUNK_OVERLAP,
                )
                for split in text_splits:
                    chunk = ChunkModel(
                        document_id=document_id,
                        filename=filename,
                        chunk_index=chunk_index,
                        page=page_num,
                        text=split,
                        embedding=[],
                    )
                    chunks.append(chunk)
                    chunk_index += 1

            if chunks:
                texts = [c.text for c in chunks]
                embeddings = await self.embedding_client.get_embeddings(texts)
                for chunk, emb in zip(chunks, embeddings):
                    chunk.embedding = emb

                await self.chunk_repo.insert_many(chunks)

            await self.doc_repo.update_status(
                doc_id=document_id,
                status=DocumentStatus.READY,
                chunks_count=len(chunks),
            )
            logger.info("Successfully processed document %s with %d chunks", document_id, len(chunks))

        except Exception as e:
            logger.error("Failed to process document %s: %s", document_id, e, exc_info=True)
            await self.doc_repo.update_status(
                doc_id=document_id,
                status=DocumentStatus.FAILED,
                error_message=str(e),
            )
