import math
from typing import List, Sequence

from agentchat.schemas.rerank import RerankResultModel
from agentchat.services.rag.embedding import get_embedding


class Reranker:

    @classmethod
    def _cosine_similarity(cls, vec1: Sequence[float], vec2: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    @classmethod
    async def bi_encoder_rerank_documents(cls, query: str, documents: List[str]):
        if not documents:
            return []

        query_embedding = await get_embedding(query)
        doc_embeddings = await get_embedding(documents)

        scored_results = []
        for idx, doc in enumerate(documents):
            score = cls._cosine_similarity(query_embedding, doc_embeddings[idx])
            scored_results.append(
                RerankResultModel(
                    query=query,
                    content=doc,
                    score=score,
                    index=idx
                )
            )

        scored_results.sort(key=lambda x: x.score, reverse=True)
        return scored_results

    @classmethod
    async def rerank_documents(cls, query, documents):
        return await cls.bi_encoder_rerank_documents(query, documents)