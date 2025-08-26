import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict, TypedDict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Chunk:
    doc_id: str
    chunk_id: int
    text: str


class LocalCorpus:
    """Load and chunk .txt files from a folder."""

    def __init__(self, data_dir: str | Path, chunk_size: int = 600, chunk_overlap: int = 80):
        self.data_dir = Path(data_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load(self) -> List[Chunk]:
        chunks: List[Chunk] = []
        for p in sorted(self.data_dir.glob("*.txt")):
            text = p.read_text(encoding="utf-8", errors="ignore")
            for i, ch in enumerate(self._split_text(text)):
                chunks.append(Chunk(doc_id=p.name, chunk_id=i, text=ch))
        return chunks

    def _split_text(self, text: str) -> List[str]:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []
        step = max(1, self.chunk_size - self.chunk_overlap)
        return [text[i : i + self.chunk_size] for i in range(0, len(text), step)]


class TfidfIndex:
    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.chunks: List[Chunk] = []

    def build(self, chunks: List[Chunk]):
        self.chunks = chunks
        docs = [c.text for c in chunks]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_df=0.9)
        self.matrix = self.vectorizer.fit_transform(docs)

    def search(self, query: str, k: int = 4) -> List[Tuple[Chunk, float]]:
        assert self.vectorizer is not None and self.matrix is not None, "Index not built"
        qv = self.vectorizer.transform([query])
        sims = cosine_similarity(qv, self.matrix)[0]
        idxs = np.argsort(-sims)[:k]
        return [(self.chunks[i], float(sims[i])) for i in idxs]


class OfflineAnswerer:
    """Simple grounded answering without external APIs.

    Strategy:
    - Concatenate top chunks into a context window.
    - Extract sentences with overlapping keywords.
    - Produce a concise answer with inline citations [doc#chunk].
    """

    def __init__(self, max_context_chars: int = 2000):
        self.max_context_chars = max_context_chars

    def answer(self, query: str, hits: List[Tuple[Chunk, float]]) -> str:
        if not hits:
            return "I couldn't find anything relevant in the local corpus."
        # Build context
        context = ""
        chosen: List[Tuple[Chunk, float]] = []
        for ch, score in hits:
            snippet = ch.text.strip()
            if len(context) + len(snippet) + 1 > self.max_context_chars:
                break
            context += ("\n" if context else "") + snippet
            chosen.append((ch, score))

        # Extractive summary: pick sentences containing query terms
        terms = set(re.findall(r"\w+", query.lower()))
        sentences = re.split(r"(?<=[.!?])\s+", context)
        picked: List[Tuple[str, Chunk]] = []
        for sent in sentences:
            toks = set(re.findall(r"\w+", sent.lower()))
            if len(terms & toks) >= max(1, round(0.2 * max(len(terms), 1))):
                # map sentence back to the first chunk that contains it
                for ch, _ in chosen:
                    if sent.strip() and sent.strip() in ch.text:
                        picked.append((sent.strip(), ch))
                        break

        if not picked:
            # fallback: first sentence of the top chunk
            top_ch, _ = chosen[0]
            picked = [(re.split(r"(?<=[.!?])\s+", top_ch.text.strip())[0], top_ch)]

        lines = []
        for sent, ch in picked[:5]:
            cite = f"[{ch.doc_id}#{ch.chunk_id}]"
            lines.append(f"- {sent} {cite}")

        return (
            "Answer (offline):\n" +
            "\n".join(lines) +
            "\n\n(This answer was composed from retrieved local text with citations.)"
        )


class OpenAIAnswerer:
    """Optional: call OpenAI to generate an answer grounded in retrieved chunks.
    Requires OPENAI_API_KEY in environment.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Use OfflineAnswerer or set the key.")

    def answer(self, query: str, hits: List[Tuple[Chunk, float]]) -> str:
        import httpx

        context_parts = []
        for ch, score in hits:
            context_parts.append(f"[{ch.doc_id}#{ch.chunk_id}]\n{ch.text.strip()}")
        context = "\n\n".join(context_parts[:6])

        system = (
            "You are a helpful assistant. Answer using ONLY the provided context. "
            "Cite sources inline like [doc#chunk]. If information is missing, say so."
        )
        user = f"Question: {query}\n\nContext:\n{context}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        # Using the Chat Completions endpoint (compatible with OpenAI-compatible providers)
        url = "https://api.openai.com/v1/chat/completions"
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
        return content


class RAGPipeline:
    def __init__(self, data_dir: str | Path, use_openai: bool = False, model: str = "gpt-4o-mini"):
        self.corpus = LocalCorpus(data_dir)
        self.index = TfidfIndex()
        self.answerer = OpenAIAnswerer(model) if use_openai else OfflineAnswerer()

    def build(self):
        chunks = self.corpus.load()
        if not chunks:
            raise RuntimeError("No .txt files found in data directory.")
        self.index.build(chunks)

    def query(self, q: str, k: int = 4) -> "QueryResult":
        hits = self.index.search(q, k=k)
        answer = self.answerer.answer(q, hits)
        sources: List[SourceDict] = [
            SourceDict(doc=ch.doc_id, chunk=ch.chunk_id, score=float(score), preview=ch.text[:160])
            for ch, score in hits
        ]
        return QueryResult(answer=answer, sources=sources)


class SourceDict(TypedDict):
    doc: str
    chunk: int
    score: float
    preview: str


class QueryResult(TypedDict):
    answer: str
    sources: List[SourceDict]

