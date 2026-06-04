from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_user
from app.ingestion.schemas import DocumentListResponse, DocumentResponse
from app.ingestion.service import delete_document, ingest_document, list_documents
from app.models import User

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_TYPES = {
    "application/pdf",
    "text/markdown",
    "text/plain",
    "text/x-markdown",
}
_MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    if file.content_type not in _ALLOWED_TYPES and not (
        file.filename or ""
    ).lower().endswith((".pdf", ".md", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, Markdown, and plain-text files are supported.",
        )

    content = await file.read()
    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 20 MB limit.",
        )

    chunk_count = await ingest_document(
        filename=file.filename or "upload",
        content=content,
        user_id=current_user.id,
        session=session,
    )
    return {"filename": file.filename, "chunks_stored": chunk_count}


@router.get("", response_model=list[DocumentListResponse])
async def get_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[dict]:
    return await list_documents(current_user.id, session)


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(
    filename: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    deleted = await delete_document(filename, current_user.id, session)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
