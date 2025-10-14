from typing import List

from prod_assistant.retriever.retrieval import Retriever
from prod_assistant.utils.model_loader import ModelLoader


class AgenticRAG:
    """
    Minimal RAG agent combining the Retriever with the configured LLM.
    """

    def __init__(self) -> None:
        self.retriever = Retriever()
        self.model_loader = ModelLoader()
        self.llm = self.model_loader.load_llm()

    async def run(self, query: str) -> str:
        """
        Retrieve context then ask the LLM to answer concisely.
        """
        docs = self.retriever.call_retriever(query)

        context_chunks: List[str] = []
        for d in docs or []:
            meta = d.metadata or {}
            context_chunks.append(
                f"Title: {meta.get('product_title', 'N/A')} | Price: {meta.get('price', 'N/A')} | Rating: {meta.get('rating', 'N/A')}\n"
                f"Reviews: {str(d.page_content)[:800]}"
            )

        context_text = "\n\n---\n\n".join(context_chunks[:4]) if context_chunks else "No retrieved context."

        prompt = (
            "You are a helpful shopping assistant. Use the provided product review context to answer the user question briefly and clearly.\n\n"
            f"User question: {query}\n\n"
            f"Context:\n{context_text}\n\n"
            "Answer:"
        )

        result = await self.llm.ainvoke(prompt)  # type: ignore
        return getattr(result, "content", str(result))


