import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

logger = logging.getLogger(__name__)


class DocumentSplitter:
    SPLITTER_TYPES = ["recursive", "character", "markdown_header"]

    @staticmethod
    def split(
        documents: List[Document],
        splitter_type: str = "recursive",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ) -> List[Document]:
        if splitter_type == "markdown_header":
            return DocumentSplitter._split_markdown_header(documents)

        if splitter_type == "character":
            splitter = CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator="\n",
            )
        else:
            if separators is None:
                separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators,
            )

        chunks = splitter.split_documents(documents)
        logger.info(
            f"Split {len(documents)} documents into {len(chunks)} chunks "
            f"using {splitter_type} splitter"
        )
        return chunks

    @staticmethod
    def _split_markdown_header(documents: List[Document]) -> List[Document]:
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
        all_chunks = []
        for doc in documents:
            try:
                chunks = splitter.split_text(doc.page_content)
                for chunk in chunks:
                    chunk.metadata.update(doc.metadata)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Markdown header split failed, falling back to recursive: {e}")
                fallback_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500, chunk_overlap=50
                )
                chunks = fallback_splitter.split_documents([doc])
                all_chunks.extend(chunks)
        return all_chunks
