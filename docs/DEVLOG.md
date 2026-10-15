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