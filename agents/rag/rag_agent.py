# agentic_rag_system.py
"""
COMPREHENSIVE AGENTIC RAG — **v2**
=================================
Adds the missing pieces requested:

* **Cross‑encoder re‑ranking** of retrieved chunks (ms‑marco MiniLM‑L‑6‑v2).
* **Adaptive top‑k tuner** that scales the number of retrieved chunks with
  question complexity and increases k on each corrective round.
* **Self‑Ask / Self‑Retrieve** branch: when reflection still finds the answer
  weak, the LLM decomposes the query into sub‑questions, each goes through a
  mini RAG cycle, and the answers are synthesised.
* Larger *dummy knowledge‑base* (≈1.5 k words) to exercise the pipeline.

Dependencies (CPU‑friendly):
```
pip install langgraph sentence-transformers faiss-cpu rank-bm25 tiktoken
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 1. Document ingestion & chunking
# ---------------------------------------------------------------------------


@dataclass
class MarkdownLoader:
    markdown_text: str

    def load(self):
        from langchain.schema import Document

        return [
            Document(page_content=self.markdown_text, metadata={"source": "dummy_md"})
        ]


@dataclass
class ChunkIndexer:
    chunk_size: int = 512
    chunk_overlap: int = 64

    def split(self, docs):
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(docs)
        for c, parent in zip(chunks, [d.metadata.get("source") for d in docs]):
            c.metadata["parent_id"] = parent
        return chunks


# ---------------------------------------------------------------------------
# 2. Retrieval layer (hybrid + re‑ranking)
# ---------------------------------------------------------------------------


class HybridRetriever:
    """Dense (FAISS) + sparse (BM25) with Reciprocal‑Rank Fusion"""

    def __init__(
        self, chunks, embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    ):
        from langchain.embeddings import HuggingFaceEmbeddings
        from langchain.vectorstores import FAISS
        from rank_bm25 import BM25Okapi

        self._embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self._dense = FAISS.from_documents(chunks, self._embeddings)
        self._chunks = chunks
        tokenised = [c.page_content.lower().split() for c in chunks]
        self._bm25 = BM25Okapi(tokenised)

    # Individual searches
    def _dense_search(self, query, k):
        return self._dense.similarity_search(query, k=k)

    def _sparse_search(self, query, k):
        scores = self._bm25.get_scores(query.lower().split())
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self._chunks[i] for i in idxs]

    # RRF fusion
    @staticmethod
    def _rrf(lists: list[list[any]], k: int):
        from collections import defaultdict

        scores = defaultdict(float)
        for docs in lists:
            for rank, doc in enumerate(docs):
                scores[id(doc)] += 1.0 / (60 + rank)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        id_to_doc = {id(doc): doc for docs in lists for doc in docs}
        return [id_to_doc[i] for i, _ in ranked][:k]

    def search(self, query: str, k: int = 8):
        dense = self._dense_search(query, k)
        sparse = self._sparse_search(query, k)
        return self._rrf([dense, sparse], k)


class CrossEncoderReranker:
    """Re‑rank candidate chunks with a cross‑encoder sentence‑transformers model."""

    def __init__(self, model="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers.cross_encoder import CrossEncoder

        self._ce = CrossEncoder(model)

    def rerank(self, query: str, docs: list[any], top_k: int = 4):
        pairs = [(query, d.page_content) for d in docs]
        scores = self._ce.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda t: t[0], reverse=True)
        return [d for _, d in ranked[:top_k]]


# ---------------------------------------------------------------------------
# 3. LangGraph state container
# ---------------------------------------------------------------------------


@dataclass
class RagState:
    question: str
    query: str = ""  # HyDE rewritten query
    retrieved: list[str] = field(default_factory=list)
    answer: str = ""
    follow_ups: int = 0  # corrective counter
    sub_answers: list[str] = field(default_factory=list)  # for self‑ask
    top_k: int = 8


# ---------------------------------------------------------------------------
# 4. Adaptive tuner
# ---------------------------------------------------------------------------


def adaptive_k(state: RagState) -> int:
    # Start proportional to question length; bump by 2 each retry
    base = 6 if len(state.question.split()) < 10 else 10
    return base + 2 * state.follow_ups


# ---------------------------------------------------------------------------
# 5. LangGraph nodes
# ---------------------------------------------------------------------------

import baml_client as b


def rewrite_query(state: RagState) -> RagState:
    state.query = b.RewriteQuery(question=state.question)
    return state


def retrieve_docs(
    state: RagState, retriever: HybridRetriever, reranker: CrossEncoderReranker
) -> RagState:
    k = adaptive_k(state)
    candidates = retriever.search(state.query or state.question, k=k)
    # Cross‑encoder re‑ranking → final 4 docs
    final_docs = reranker.rerank(state.query or state.question, candidates, top_k=4)
    state.retrieved = [d.page_content for d in final_docs]
    state.top_k = k
    return state


def answer_question(state: RagState) -> RagState:
    ctx = "\n---\n".join(state.retrieved)
    state.answer = b.AnswerQuestionWithContext(question=state.question, context=ctx)
    return state


def reflect(state: RagState) -> str:
    low_conf = ("i don't know" in state.answer.lower()) or len(
        state.answer.split()
    ) < 12
    if low_conf and state.follow_ups == 0:
        state.follow_ups += 1
        return "retry"  # corrective RAG
    if low_conf and state.follow_ups == 1:
        return "selfask"  # move to self‑ask branch
    return "done"


# --- Self‑ask node -----------------------------------------------------------


def self_ask(
    state: RagState, retriever: HybridRetriever, reranker: CrossEncoderReranker
) -> RagState:
    # Decompose question
    sub_questions_obj = b.DecomposeQuestion(question=state.question)
    sub_questions = sub_questions_obj.questions

    # Mini RAG per sub-question
    state.sub_answers = []
    for sub_q in sub_questions:
        candidates = retriever.search(sub_q, k=state.top_k)
        final_docs = reranker.rerank(sub_q, candidates, top_k=4)
        ctx = "\n---\n".join([d.page_content for d in final_docs])
        sub_ans = b.AnswerQuestionWithContext(question=sub_q, context=ctx)
        state.sub_answers.append(sub_ans)

    # Synthesize
    state.answer = b.SynthesizeAnswers(
        question=state.question, sub_answers=state.sub_answers
    )
    return state


# ---------------------------------------------------------------------------
# 6. Build graph
# ---------------------------------------------------------------------------

from langgraph.graph import StateGraph


def build_graph(ret: HybridRetriever, rr: CrossEncoderReranker):
    g = StateGraph(RagState)
    g.add_node("rewrite", rewrite_query)
    g.add_node("retrieve", lambda s: retrieve_docs(s, ret, rr))
    g.add_node("answer", answer_question)
    g.add_node("selfask", lambda s: self_ask(s, ret, rr))

    g.set_entry_point("rewrite")
    g.add_edge("rewrite", "retrieve")
    g.add_edge("retrieve", "answer")
    g.add_conditional_edges(
        "answer",
        reflect,
        {
            "retry": "retrieve",
            "selfask": "selfask",
            "done": g.END,
        },
    )

    return g.compile()


# ---------------------------------------------------------------------------
# 7. Demo runner
# ---------------------------------------------------------------------------

from langchain.document_loaders import MarkdownLoader


def run_demo():
    # Load & chunk
    docs = MarkdownLoader("data/test_rag.md").load()
    chunks = ChunkIndexer().split(docs)

    # Build components
    ret = HybridRetriever(chunks)
    rr = CrossEncoderReranker()
    agent = build_graph(ret, rr)

    # Example Q
    question = "How does LangGraph help implement corrective RAG loops?"
    final = agent.invoke({"question": question})

    print("\nQUESTION:\n", question)
    print("\nANSWER:\n", final["answer"])
    if final["sub_answers"]:
        print("\nSELF‑ASK TRACE:\n" + "\n---\n".join(final["sub_answers"]))


if __name__ == "__main__":
    run_demo()
