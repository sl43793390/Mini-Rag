import logging
from typing import List, Optional, Generator

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma

from config import (
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    LLM_MODEL,
    CHROMA_PERSIST_DIR,
)

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """你是一个专业的知识库问答助手。请根据以下检索到的上下文内容来回答用户的问题。
如果你无法从上下文中找到答案，请诚实地说明，不要编造信息。
请用中文回答。

上下文内容：
{context}

用户问题：{question}

回答："""


def _normalize_api_base(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


class EmbeddingManager:
    def __init__(self):
        self._embeddings = None
        self._llm = None
        self._api_base = _normalize_api_base(OPENAI_API_BASE)
        self._vectorstore_cache = {}

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            kwargs = {
                "model": EMBEDDING_MODEL,
                "api_key": OPENAI_API_KEY,
                "base_url": self._api_base,
            }
            if EMBEDDING_DIMENSIONS > 0:
                kwargs["dimensions"] = EMBEDDING_DIMENSIONS
            self._embeddings = OpenAIEmbeddings(**kwargs)
        return self._embeddings

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=LLM_MODEL,
                api_key=OPENAI_API_KEY,
                base_url=self._api_base,
                temperature=0.7,
                streaming=True,
            )
        return self._llm

    def get_vectorstore(self, collection_name: str) -> Chroma:
        if collection_name not in self._vectorstore_cache:
            self._vectorstore_cache[collection_name] = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=CHROMA_PERSIST_DIR,
            )
        return self._vectorstore_cache[collection_name]

    def add_documents(
        self,
        documents: List[Document],
        collection_name: str,
    ) -> int:
        vectorstore = self.get_vectorstore(collection_name)
        try:
            ids = vectorstore.add_documents(documents)
            logger.info(
                f"Added {len(ids)} documents to collection '{collection_name}'"
            )
            return len(ids)
        except Exception as e:
            logger.error(f"Error adding documents to '{collection_name}': {e}")
            raise RuntimeError(
                f"向量化存入失败，请检查 API 配置是否正确（API Key、API Base URL、Embedding 模型名称）。"
                f"原始错误: {e}"
            ) from e

    def delete_collection(self, collection_name: str) -> bool:
        try:
            if collection_name in self._vectorstore_cache:
                del self._vectorstore_cache[collection_name]
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=CHROMA_PERSIST_DIR,
            )
            vectorstore.delete_collection()
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection '{collection_name}': {e}")
            return False

    def get_retriever(
        self,
        collection_name: str,
        search_kwargs: Optional[dict] = None,
    ):
        vectorstore = self.get_vectorstore(collection_name)
        if search_kwargs is None:
            search_kwargs = {"k": 4}
        return vectorstore.as_retriever(search_kwargs=search_kwargs)

    def query(
        self,
        question: str,
        collection_name: str,
        top_k: int = 4,
    ) -> List[Document]:
        retriever = self.get_retriever(
            collection_name, search_kwargs={"k": top_k}
        )
        docs = retriever.invoke(question)
        return docs

    def generate_answer(
        self,
        question: str,
        documents: List[Document],
    ) -> str:
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        context_text = "\n\n".join(doc.page_content for doc in documents)

        chain = prompt | self.llm | StrOutputParser()

        return chain.invoke({"context": context_text, "question": question})

    def stream_generate_answer(
        self,
        question: str,
        documents: List[Document],
    ) -> Generator[str, None, None]:
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        context_text = "\n\n".join(doc.page_content for doc in documents)

        chain = prompt | self.llm | StrOutputParser()

        for chunk in chain.stream({"context": context_text, "question": question}):
            yield chunk

    def chat(
        self,
        question: str,
        collection_name: str,
        top_k: int = 4,
    ) -> str:
        docs = self.query(question, collection_name, top_k)
        return self.generate_answer(question, docs)

    def get_collection_count(self, collection_name: str) -> int:
        try:
            vectorstore = self.get_vectorstore(collection_name)
            return vectorstore._collection.count()
        except Exception:
            return 0
