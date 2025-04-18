# Retrieval‑Augmented Generation Handbook

Retrieval‑Augmented Generation (RAG) couples an information
retriever with a large language model. It boosts factuality,
reduces hallucination, and allows small models to punch above their
weight.

## Key Concepts

* **Hybrid Retrieval** leverages both lexical (BM25) and semantic
  (vector) search to maximise recall.
* **Cross‑Encoder Re‑ranking** applies a deeper model over candidate
  passages to refine precision.
* **HyDE Query Rewriting** transforms a question into a hypothetical
  answer so its embedding captures richer context.
* **Self‑Ask / Self‑Retrieve** breaks complex queries into smaller
  ones that can each be answered with higher confidence.
* **Corrective RAG** detects weak answers and performs follow‑up
  retrievals.

## LangGraph

LangGraph is a Python framework that lets you declare agentic
workflows as graphs. Each node is a function that mutates a
structured state object; edges and conditional edges dictate
questions ↔ retrieval ↔ generation loops.

### Example

```python
graph = StateGraph(RagState)
graph.add_node('retrieve', retrieve_fn)
graph.add_node('answer', answer_fn)
graph.add_conditional_edges('answer', decide_fn, {'retry': 'retrieve'})
```

## FAQ

**Q:** What is parent‑document retrieval?
**A:** After finding a highly relevant chunk, fetch its parent doc to
provide more context and avoid truncation errors.
---

Beyond retrieval, RAG systems benefit from evaluation metrics like
precision@k, groundedness scores, and human‑in‑the‑loop audits.