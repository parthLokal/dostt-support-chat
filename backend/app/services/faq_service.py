"""Keyword-scored FAQ lookup. This is the mocked-AI seam described in
README.md: in production `search` would likely still exist (Gemini is meant
to look answers up, per the chatbot PRD, never invent them) but a real
deployment could also lean on Gemini itself to pick the best match from the
full FAQ list. Word-set matching (not exact phrase order) so free text like
"my wallet balance is negative" still matches the "negative balance" keyword.
"""

import re

from app.data.faqs import FAQS, Faq

_WORD_RE = re.compile(r"[a-z0-9]+")


def _stem(word: str) -> str:
    """Light suffix-stripping so "crashing"/"crashed"/"crashes" all match a
    "crash"-rooted keyword — not real stemming, just enough to cover the
    common English inflections that show up in free-typed complaints."""
    for suffix in ("ing", "edly", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _score(text_lower: str, text_stems: set[str], faq: Faq) -> int:
    score = 0
    for kw in faq.keywords:
        if kw in text_lower:
            score += len(kw.split()) * 2
            continue
        kw_stems = [_stem(w) for w in kw.split()]
        if len(kw_stems) > 1 and all(s in text_stems for s in kw_stems):
            score += len(kw_stems)
        elif len(kw_stems) == 1 and kw_stems[0] in text_stems:
            score += 1
    return score


def search(query: str, *, audience: str | None = None) -> Faq | None:
    text_lower = query.lower()
    text_stems = {_stem(w) for w in _WORD_RE.findall(text_lower)}
    candidates = [f for f in FAQS if audience is None or f.audience in ("both", audience)]
    scored = [(f, _score(text_lower, text_stems, f)) for f in candidates]
    scored = [pair for pair in scored if pair[1] > 0]
    if not scored:
        return None
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[0][0]


def get(faq_id: str) -> Faq | None:
    from app.data.faqs import FAQS_BY_ID

    return FAQS_BY_ID.get(faq_id)


_DOMAIN_WORDS = {
    "call", "coin", "coins", "refund", "wallet", "recharge", "listener", "sdt", "dostt",
    "video", "audio", "account", "app", "withdraw", "payout", "kyc", "pan", "tds",
    "language", "gender", "block", "ticket", "voice", "face", "earning", "upi", "profile",
}


def looks_app_related(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _DOMAIN_WORDS)


def looks_like_gibberish(text: str) -> bool:
    trimmed = text.strip()
    if len(trimmed) < 2:
        return True
    letters = re.sub(r"[^a-zA-Z]", "", trimmed)
    return len(letters) >= 4 and not re.search(r"[aeiouAEIOU]", letters)
