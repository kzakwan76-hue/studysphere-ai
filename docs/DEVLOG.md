# Development log

## Milestone 1: foundation and accounts
**Built:** project scaffold, settings, SQLAlchemy models, Alembic migrations, register/login/me, tests, CI.

**Decisions**
- Migrations from day one instead of `create_all`, with a test that checks migrations match the models.
- The app refuses to start with a `SECRET_KEY` shorter than 32 characters.
- Paths are computed from the file location, so commands work from any folder.

**Problems and fixes**
- (add yours here as they happen)

## Milestone 3: search
**Built:** tokenizer with light stemming, BM25 from scratch, /search endpoint (per-user, page references), coverage signal, retrieval evaluation harness with 5 synthetic documents and 26 questions.

**Decisions**
- BM25 instead of embeddings first: no API key, no cost, and every line is explainable. Embeddings can plug in later behind the same interface.
- Coverage (share of question terms found) is returned next to the BM25 score because BM25 scores are not comparable across searches; Milestone 4 needs a "relevant enough?" signal.
- The index is rebuilt per search; fine for personal study libraries, caching is a later optimisation.
- Query text is not logged, only counts, because it may contain private study content.

**Results** (paste real numbers from `python scripts\eval_retrieval.py`)
- hit@1 / hit@3 / hit@5 / MRR: ...
- Observations: ...

**Limitations**
- Synthetic corpus of 5 short documents with questions written by me, so results are optimistic.
- Keyword matching cannot match different words with the same meaning (synonyms, "halving" vs "halves").

**Results** (`python scripts\eval_retrieval.py`; easy set: 19 answerable + 7 unanswerable questions, 5 documents, 10 chunks)
- hit@1 = hit@3 = hit@5 = 1.00, MRR = 1.00. The corpus is tiny (random guessing would get about 10% at rank 1) and the questions share vocabulary with the documents, so this is a smoke test, not a quality claim.
- Coverage of the top result: a threshold of 0.6 keeps 18 of 19 answerable questions (0.95) and none of the 7 unanswerable ones. At 0.5 the same 18 are kept but the Dijkstra question (0.50) slips through, because it shares "time", "complexity" and "algorithm" with the sorting notes.
- Caution: 0 of 7 wrongly kept is a small sample (the true rate could plausibly be near 40%), and a threshold chosen on this set has not been validated on another. Coverage alone is not enough; Milestone 4 adds model-side refusal and citation checks.
- Hard set (paraphrased questions and topic-related unanswerable ones): (add after running it)