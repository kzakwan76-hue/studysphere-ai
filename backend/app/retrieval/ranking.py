"""Combine tokenizing and BM25: rank passages for a query and say how well each one matches."""

from dataclasses import dataclass

from app.retrieval.bm25 import BM25Index
from app.retrieval.tokenizer import tokenize


@dataclass(frozen=True)
class RankedPassage:
    index: int  # position in the list of texts that was passed in
    score: float  # BM25 score: only meaningful for comparing passages within one search
    coverage: float  # share of the query's distinct terms found in the passage (0 to 1)
    matched_terms: list[str]


def rank_passages(query: str, texts: list[str], limit: int = 5) -> tuple[list[str], list[RankedPassage]]:
    """Return (the query's search terms, the best passages). No terms or no match gives no passages."""
    query_terms = list(dict.fromkeys(tokenize(query)))  # distinct, in the order they were asked
    if not query_terms or not texts:
        return query_terms, []

    index = BM25Index([tokenize(text) for text in texts])
    ranked: list[RankedPassage] = []
    for hit in index.search(query_terms, limit):
        present = index.terms_in(hit.index)
        matched = [term for term in query_terms if term in present]
        ranked.append(RankedPassage(hit.index, hit.score, len(matched) / len(query_terms), matched))
    return query_terms, ranked