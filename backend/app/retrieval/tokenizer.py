"""Turning text into search terms: lowercase, split into words, drop filler words, light stemming."""

import re

_WORD = re.compile(r"[^\W_]+")  # runs of letters and digits in any language (no underscores)

STOPWORDS = frozenset(
    """
    a about above after again against all also am an and any are as at be because been before being below
    between both but by can could did do does doing down during each few for from further had has have having
    he her here hers him his how i if in into is it its itself just many me more most much my no nor not now
    of off on once only or other our ours out over own same she should so some such than that the their theirs
    them then there these they this those through to too under until up very was we were what when where which
    while who whom why will with would you your yours
    """.split()
)


def stem(word: str) -> str:
    """A deliberately light stemmer: searches, searching and searched all become 'search'.

    It is not perfect (halves -> halve but halving -> halv). What matters is that the same rule is
    applied to documents and to questions, so words are reduced consistently.
    """
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith(("ches", "shes", "sses")):
        return word[:-2]
    if len(word) > 6 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 5 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """Split text into search terms. Repeats are kept, because BM25 counts them."""
    terms: list[str] = []
    for match in _WORD.finditer(text.lower()):
        word = match.group()
        if len(word) < 2 or word in STOPWORDS:
            continue
        terms.append(stem(word))
    return terms