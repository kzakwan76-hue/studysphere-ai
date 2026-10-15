"""BM25 ranking, implemented from scratch.

BM25 scores how well a passage matches a query using three ideas:
  1. Rare words matter more than common ones (inverse document frequency).
  2. Repeating a word helps, but with diminishing returns (term-frequency saturation).
  3. A match in a short passage is worth more than the same match in a long one (length normalisation).
"""

import math
from collections import Counter
from dataclasses import dataclass

K1 = 1.5  # how quickly repeating a word stops adding score
B = 0.75  # how strongly long passages are penalised


@dataclass(frozen=True)
class ScoredDocument:
    index: int  # position in the list the index was built from
    score: float


class BM25Index:
    def __init__(self, documents: list[list[str]], k1: float = K1, b: float = B) -> None:
        self._k1 = k1
        self._b = b
        self._counts = [Counter(tokens) for tokens in documents]
        self._lengths = [len(tokens) for tokens in documents]
        self._average_length = sum(self._lengths) / len(documents) if documents else 0.0

        document_frequency: Counter[str] = Counter()
        self._postings: dict[str, list[int]] = {}  # term -> positions of the documents containing it
        for position, counts in enumerate(self._counts):
            for term in counts:
                document_frequency[term] += 1
                self._postings.setdefault(term, []).append(position)

        total = len(documents)
        # This IDF variant is never negative, even for a word that appears in every document.
        self._idf = {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def terms_in(self, position: int) -> set[str]:
        return set(self._counts[position])

    def search(self, query_terms: list[str], limit: int = 5) -> list[ScoredDocument]:
        """The best-scoring documents, best first. Ties are broken by position, so results are stable."""
        if self._average_length == 0:
            return []
        scores: dict[int, float] = {}
        for term in sorted(set(query_terms)):
            if term not in self._idf:
                continue
            for position in self._postings[term]:
                count = self._counts[position][term]
                length_factor = 1 - self._b + self._b * self._lengths[position] / self._average_length
                scores[position] = scores.get(position, 0.0) + self._idf[term] * (
                    count * (self._k1 + 1) / (count + self._k1 * length_factor)
                )
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [ScoredDocument(position, score) for position, score in ranked[:limit]]