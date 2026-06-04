import uuid
from io import BytesIO

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Document

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def _extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from PDF or markdown/text file."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    # Treat everything else (markdown, txt) as plain text
    return content.decode("utf-8", errors="replace")


async def ingest_document(
    filename: str,
    content: bytes,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> int:
    """Parse, chunk, embed, and persist a document. Returns the number of chunks stored."""
    text = _extract_text(filename, content)
    chunks = _splitter.split_text(text)
    if not chunks:
        return 0

    embeddings_model = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    vectors = await embeddings_model.aembed_documents(chunks)

    # Remove any previous version of this file for this user
    await session.execute(
        delete(Document).where(
            Document.user_id == user_id,
            Document.filename == filename,
        )
    )

    documents = [
        Document(
            user_id=user_id,
            filename=filename,
            chunk_index=i,
            content=chunk,
            embedding=vector,
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    session.add_all(documents)
    await session.commit()
    return len(documents)


async def list_documents(
    user_id: uuid.UUID, session: AsyncSession
) -> list[dict]:
    """Return unique filenames with chunk count and earliest created_at."""
    result = await session.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.filename, Document.chunk_index)
    )
    rows = result.scalars().all()

    seen: dict[str, dict] = {}
    for doc in rows:
        if doc.filename not in seen:
            seen[doc.filename] = {"filename": doc.filename, "chunk_count": 0, "created_at": doc.created_at}
        seen[doc.filename]["chunk_count"] += 1
    return list(seen.values())


async def delete_document(
    filename: str, user_id: uuid.UUID, session: AsyncSession
) -> bool:
    """Delete all chunks for a filename owned by user. Returns True if anything was deleted."""
    result = await session.execute(
        delete(Document).where(
            Document.user_id == user_id,
            Document.filename == filename,
        ).returning(Document.id)
    )
    await session.commit()
    return result.rowcount > 0


async def search_documents(
    query: str,
    user_id: uuid.UUID,
    session: AsyncSession,
    top_k: int = 5,
) -> list[str]:
    """Semantic search over a user's uploaded documents. Returns top-k chunk texts."""
    embeddings_model = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    query_vector = await embeddings_model.aembed_query(query)

    result = await session.execute(
        select(Document.content)
        .where(Document.user_id == user_id)
        .order_by(Document.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    return list(result.scalars().all())
