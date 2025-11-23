# qdrantPEPsearch

**Final Project: Production-Ready Documentation Search Engine**

**High-Level Summary**

- **Domain:** "Documentation search for Python PEPs"
- **Key Result:** "Hybrid + multivector reranking reached Recall@10=0.818 with P95 latency ≈ 268ms."
- **Project description:** "This project implements a documentation search engine for Python PEPs. It starts with a
  custom parser that extracts PEP sections and relevant metadata, which are then streamed into a pre-created Quadrant
  collection in real-time. Several indices were built to support hybrid search with dense, sparse, and multivector
  embeddings. An evaluation module measures performance metrics such as Recall@10 and MRR. All tests and
  configurations—including search parameters, reranker settings, and index limits—are defined in YAML for convenience
  and reproducibility, enabling easy experimentation with different setups."

**Reproducibility**

- **Notebook/App:** https://github.com/subbota19/qdrantPEPsearch/blob/main/search/search.py
- **Repo (optional):** https://github.com/subbota19/qdrantPEPsearch
- **Models:** dense=BAAI/bge-base-en-v1.5, sparse=prithivida/Splade_PP_en_v1, colbert=colbert-ir/colbertv2.0
- **Collection:** docs_search (Cosine), points=19433
- **Dataset:** PEP snapshot from peps.python.org (snapshot: 2025-11-10)
- **Ground truth:** 27 queries (how-to / concept / api / troubleshooting)

**Settings (today)**

- **Chunking:** one section per heading
- **Payload fields:** page_title, status, section_title, page_url, section_url, breadcrumbs, chunk_text,
  prev_section_text, next_section_text, tags
- **Fusion:** RRF, k_dense=100, k_sparse=100
- **Reranker:** ColBERT (MaxSim), top-k=30

**Queries (examples)**

* "how to declare async function"

Top 3:

1. score: 23.1591
   PEP: Coroutines with async and await syntax
   URL: https://peps.python.org/pep-0492/#glossary
   Snippet: A coroutine function is declared with async def. It uses await and return value; see New Coroutine
   Declaration Syntax for details.
2. score: 21.7571
   PEP: Coroutines with async and await syntax
   URL: https://peps.python.org/pep-0492/#why-async-def-and-not-def-async
   Snippet: async keyword is a statement qualifier. A good analogy to it are “static”, “public”, “unsafe” keywords from
   other languages. “async for” is an asynchronous “for” statement, “async with” is an asynchronous “with” statement,
   “async def” is an asynchronous function.
3. score: 21.6984
   PEP: Asynchronous Generators
   URL: https://peps.python.org/pep-0525/#backwards-compatibility
   Snippet: In Python 3.5 it is a SyntaxError to define an async def function with a yield expression inside, therefore
   it’s safe to introduce asynchronous generators in 3.6.

* "how does it allocate memory for objects of different sizes"

Top 3:

1. score=20.3954
   PEP: Add new APIs to customize Python memory allocators
   URL: https://peps.python.org/pep-0445/#new-functions-and-structures
   Snippet: Note The pymalloc allocator is optimized for objects smaller than 512 bytes with a short lifetime. It uses
   memory mappings with a fixed size of 256 KB called “arenas”.
2. score=20.3210
   PEP: Add new APIs to customize Python memory allocators
   URL: https://peps.python.org/pep-0445/#memory-allocators
   Snippet: To allocate memory on the heap, an allocator tries to reuse free space. If there is no contiguous space big
   enough, the heap must be enlarged, even if there is more free space than required size. This issue is called the
   “memory fragmentation”: the memory usage seen by the system is higher than real usage. On Windows, HeapAlloc()
   creates a new memory mapping with VirtualAlloc() if there is not enough free contiguous memory.
3. score=19.9952
   PEP: Add new APIs to customize Python memory allocators
   URL: https://peps.python.org/pep-0445/#memory-allocators
   Snippet: CPython has a pymalloc allocator for allocations smaller than 512 bytes. This allocator is optimized for
   small objects with a short lifetime. It uses memory mappings called “arenas” with a fixed size of 256 KB.

**Evaluation**

- Recall@10: 0.818 | MRR: 0.590 | P50: 0.230s | P95: 0.264s

**Why these matched**

The hybrid search with RRF fusion and ColBERT reranking effectively combined dense semantic understanding with sparse
keyword matching. Top results align with the user queries because the multivector stage accurately scores both
token-level relevance and contextual similarity, ensuring that authoritative PEP sections appear first. The small size
of the asset means that recall is high across most configurations, which explains why results are very consistent.

**Surprise**

Despite varying RFF limits and aggressive hybrid settings, the Recall@10 remained nearly identical across all
configurations. This indicates that for a relatively small and well-structured dataset like the PEP corpus, fusion alone
captures most of the relevant sections. The difference in latency was negligible, suggesting that the reranker dominates
runtime for top-k candidate scoring.

**Next step**

Add a filter based on status by creating a dedicated index for it. This will allow the search engine to selectively
retrieve only relevant sections, improving practical usability and supporting conditional filtering in queries.