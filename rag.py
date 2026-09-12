"""RAG retrieval + grounded generation via Groq."""
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import prompts as P

load_dotenv()

ROOT = Path(__file__).parent
INDEX_DIR = ROOT / "faiss_index"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_vs():
    if not INDEX_DIR.exists():
        raise FileNotFoundError("faiss_index not found. Run `python ingest.py` first.")
    emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return FAISS.load_local(str(INDEX_DIR), emb, allow_dangerous_deserialization=True)


def rag_search(question: str, k: int = 4) -> dict:
    vs = _load_vs()
    docs = vs.similarity_search(question, k=k)
    if not docs:
        return {
            "answer": "I don't have enough information in the knowledge base to answer this reliably.",
            "sources": [],
            "retrieved": [],
        }

    context = "\n\n---\n\n".join(d.page_content for d in docs)
    titles = list(dict.fromkeys(
        d.metadata.get("source_title", d.metadata.get("source", "unknown")) for d in docs))

    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    chain = PromptTemplate.from_template(P.RAG_PROMPT) | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    return {"answer": answer, "sources": titles, "retrieved": [d.metadata for d in docs]}


if __name__ == "__main__":
    import json
    print(json.dumps(rag_search("What are must-visit attractions in Singapore?"), indent=2))