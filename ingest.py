"""Ingest knowledge base into a FAISS vector store."""
import re
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

ROOT = Path(__file__).parent
KB_DIR = ROOT / "data" / "knowledge_base"
INDEX_DIR = ROOT / "faiss_index"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def parse_source(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<!--\s*source_title:\s*(.*?)\s*\|\s*source_url:\s*(.*?)\s*-->", text)
    title = m.group(1).strip() if m else path.stem
    url = m.group(2).strip() if m else ""
    return title, url


def main():
    docs = []
    for f in sorted(KB_DIR.glob("*.md")):
        title, url = parse_source(f)
        text = f.read_text(encoding="utf-8")
        docs.append(Document(
            page_content=text,
            metadata={"source": f.name, "source_title": title, "source_url": url},
        ))
        print(f"Loaded {f.name} — title: {title}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    counts = {}
    for c in chunks:
        counts[c.metadata["source"]] = counts.get(c.metadata["source"], 0) + 1
    print("\nChunks per source:")
    for src, n in counts.items():
        print(f"  {src}: {n}")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vs = FAISS.from_documents(chunks, embeddings)
    INDEX_DIR.mkdir(exist_ok=True)
    vs.save_local(str(INDEX_DIR))
    print(f"\nSaved FAISS index to {INDEX_DIR}")


if __name__ == "__main__":
    main()