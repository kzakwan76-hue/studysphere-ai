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

## Milestone 4: grounded answers
**Built:** /ask endpoint; provider interface (none, ollama, anthropic); numbered-excerpt prompt; relevance gate; citation verification; support-score warning; per-user hourly rate limit; answer evaluation script; demo_upload.py and demo_ask.py.

**Decisions**
- The model is never called when the best passage matches too few of the question's key words (ANSWER_MIN_COVERAGE, default 0.5).
- An answer is only shown if it cites passages and every citation exists; otherwise it is withheld and the passages are shown instead.
- Passages and filenames are untrusted: angle brackets are neutralised so they cannot close prompt tags, and the system prompt says never to follow instructions inside excerpts.
- The support score is a heuristic (word overlap), shown as a warning, never as proof of correctness.
- Default provider is "none", so the app works with no key or cost. No database change, so no migration; chat history comes with the frontend.

**Results** (provider: ollama, model: llama3.2, temperature 0, min coverage 0.5, single run per set)

| | Default set (`retrieval_questions.json`) | Hard set (`retrieval_questions_hard.json`) |
|---|---|---|
| Answerable questions | 19 | 12 |
| Answered | 18 | 4 |
| False refusals (answerable but refused) | 1/19 | 8/12 |
| Answered with the expected passage cited | 17/19 | 4/12 |
| Unanswerable questions | 7 | 6 |
| Correctly refused | 7/7 | 4/6 |
| Unanswerable but answered anyway | 0/7 | 2/6 |

**Findings**
- On the default set the pipeline behaved as designed: no unanswerable question was answered, and 17 of 19 answerable questions got an answer citing the expected passage. One answered question did not cite the expected passage.
- No `unverified` results appeared in either run, so llama3.2 followed the citation format on these question sets.
- On the hard set the pipeline performed much worse: 8 of 12 answerable questions were refused, and 2 of 6 unanswerable questions were answered anyway. When it did answer an answerable question, the right passage was cited (4/4).
- The evaluation script reports both the coverage gate and the model's INSUFFICIENT_INFORMATION reply as `not_found`, so these results do not show which one caused the 8 false refusals. Separating them is the next diagnostic step.
- The 2 unanswerable questions that were answered anyway mean a passage passed the relevance gate and the model produced a cited answer. The citation check only proves a cited passage exists, not that it answers the question.
- Both sets are small (26 and 18 questions), so one question changes the percentages noticeably. These are single runs and should be treated as indicative, not as precise rates.


Answerable but refused (false refusals): 1/19
Unanswerable and refused (correct):      6/7

**Limitations**
- The rate limiter is in memory (per process, resets on restart).
- The gate threshold was chosen on a small synthetic set and has not been validated on held-out questions.
- Small local models often break the citation format, which shows up as "unverified" results.
- The gate threshold (0.5) was tuned on the default question set, and the hard set shows it does not generalise well. Evaluation results come from small question sets and single runs.

## Milestone 5: frontend
**Built:** Vite + React + TypeScript + Tailwind app with registration/login, document upload/list/delete, and an Ask page that shows the status, answer, warnings and numbered sources.

**Decisions**
- The Vite dev server proxies /api to FastAPI, so the backend needed no CORS changes.
- The login token is stored in localStorage (simple, but readable by any script on the page; fine for local development, to be revisited before deployment).
- Answers and passages are rendered as plain text only; React escapes them, and dangerouslySetInnerHTML is never used.
- An expired session (401) logs the person out automatically.

**Limitations**
- No automated frontend tests yet.
- No subject organisation, chat history or document filter in the UI yet.

## Milestone 6: subjects and dashboard
**Built:** subjects (create, list, delete); assigning documents to a subject; GET /dashboard; /ask scoped to a subject; frontend Dashboard tab (stats, subjects, upload, assign) and a subject picker on the Ask tab.

**Decisions**
- Subject membership lives in a new subject_documents table instead of a column on documents. The migration only creates tables, so the existing documents and chunks are never rebuilt (rebuilding a SQLite table with foreign keys on can cascade-delete rows).
- A document is in at most one subject (document_id is the primary key). Deleting a subject keeps its documents.
- Every subject query is scoped to the logged-in user, and someone else's subject or document looks the same as a missing one (404).
- /ask accepts a document or a subject, not both.
- The migration was written by hand to follow login_failures (66eaa1e25439).

**Limitations**
- Subject names are compared case-insensitively with SQL lower(), which is reliable for English letters only.
- The dashboard returns all documents in one response (limited to 50 per user by the upload cap).
- No automated frontend tests yet.