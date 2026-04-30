# =============================================================================
# nlp.py — OCR Text Cleaning & Preprocessing
# =============================================================================
# Dependencies:
#   spacy (en_core_web_sm), rapidfuzz, scikit-learn
# =============================================================================

from __future__ import annotations

import logging
import re
from functools import lru_cache

from rapidfuzz import fuzz, process
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

__all__ = ["preprocess_for_tfidf", "preprocess_for_sbert", "preprocess_markdown_for_sbert", "split_sentences"]

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"\b\w+\b")
_TOKEN_OR_SEPARATOR_PATTERN = re.compile(r"\w+|\W+")
_FUZZY_SCORE_THRESHOLD = 80
_FUZZY_MARGIN_THRESHOLD = 5
_MIN_FUZZY_WORD_LENGTH = 4

_OCR_TRANSLATION_TABLE = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
)


# --------------------------------------------------------------------------- #
#  Domain vocabularies and heuristics                                          #
# --------------------------------------------------------------------------- #

DOMAIN_VOCAB: dict[str, tuple[str, ...]] = {
    "cloud": (
        "application",
        "chart",
        "configuration",
        "crd",
        "deployment",
        "helm",
        "integration",
        "kubernetes",
        "postgresql",
        "redis",
        "serverless",
        "service",
        "template",
        "yaml",
    )
}

DOMAIN_HINTS: dict[str, frozenset[str]] = {
    "cloud": frozenset({"helm", "kubernetes", "yaml"})
}

_PROTECTED_COMMON_WORDS = frozenset(ENGLISH_STOP_WORDS).union(
    {
        "answer",
        "class",
        "design",
        "effect",
        "explain",
        "method",
        "model",
        "paper",
        "process",
        "question",
        "result",
        "student",
        "system",
        "theory",
    }
)

_SPLIT_SUFFIXES = frozenset(
    {
        "able",
        "ation",
        "ality",
        "ative",
        "ence",
        "ency",
        "ible",
        "ical",
        "ified",
        "ifier",
        "iness",
        "ingly",
        "integration",
        "isation",
        "ization",
        "ition",
        "itive",
        "ively",
        "lement",
        "lessly",
        "logy",
        "ment",
        "ments",
        "ness",
        "ology",
        "sion",
        "tion",
    }
)


# --------------------------------------------------------------------------- #
#  Cached helpers                                                              #
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _all_domain_terms() -> frozenset[str]:
    """Flatten every configured domain vocabulary into a single lookup set."""
    return frozenset(term for vocab in DOMAIN_VOCAB.values() for term in vocab)


@lru_cache(maxsize=1)
def _stop_words() -> frozenset[str]:
    """Return a cached stopword set for lightweight lexical preprocessing."""
    return frozenset(ENGLISH_STOP_WORDS)


# --------------------------------------------------------------------------- #
#  Lazy-loaded spaCy model (avoids import-time cost if unused)                 #
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _get_spacy_nlp():
    """Load the spaCy model lazily and cache it for reuse."""
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:
        raise OSError(
            "spaCy model not found. Run: python -m spacy download en_core_web_sm"
        ) from exc


# --------------------------------------------------------------------------- #
#  Step 1: Basic text sanitization                                             #
# --------------------------------------------------------------------------- #

def _sanitize(text: str) -> str:
    """Normalize OCR text while preserving sentence structure for SBERT."""
    text = text.translate(_OCR_TRANSLATION_TABLE).lower()
    text = text.encode("ascii", errors="ignore").decode()

    # Keep punctuation that helps sentence encoders and remove OCR garbage.
    text = re.sub(r"[^a-z0-9\s\.,;:!?\-/'()%]", " ", text)

    # Collapse repeated punctuation and whitespace noise.
    text = re.sub(r"([.,;:!?])\1+", r"\1", text)
    text = re.sub(r"-{2,}", "-", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# --------------------------------------------------------------------------- #
#  Step 2: OCR split-word repair                                               #
# --------------------------------------------------------------------------- #

def _should_merge_split(left: str, right: str) -> bool:
    """Decide whether two adjacent OCR tokens should be merged."""
    if not (left.isalpha() and right.isalpha()):
        return False

    if len(left) < 3 or len(right) < 2:
        return False

    merged = f"{left}{right}"
    if merged in _all_domain_terms():
        return True

    # Handle generic OCR breaks like "applica tion" without over-merging.
    if len(merged) >= 8 and right in _SPLIT_SUFFIXES:
        return True

    return False


def _fix_split_words(text: str) -> str:
    """Merge OCR-split words while preserving surrounding punctuation."""
    parts = _TOKEN_OR_SEPARATOR_PATTERN.findall(text)
    if not parts:
        return text

    merged_parts: list[str] = []
    index = 0

    while index < len(parts):
        current = parts[index]

        if (
            index + 2 < len(parts)
            and current.isalpha()
            and parts[index + 1].isspace()
            and parts[index + 2].isalpha()
            and _should_merge_split(current, parts[index + 2])
        ):
            merged_parts.append(f"{current}{parts[index + 2]}")
            index += 3
            continue

        merged_parts.append(current)
        index += 1

    return "".join(merged_parts)


# --------------------------------------------------------------------------- #
#  Step 3: Domain detection and OCR-aware fuzzy correction                     #
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=512)
def _detect_domain(text: str) -> str | None:
    """Infer the text domain using lightweight exact-match heuristics."""
    tokens = set(_TOKEN_PATTERN.findall(text.lower()))

    for domain, hints in DOMAIN_HINTS.items():
        if hints.issubset(tokens):
            return domain

    return None


@lru_cache(maxsize=8192)
def _fuzzy_match(word: str, vocab: tuple[str, ...]) -> str:
    """Return a safe domain correction using the top RapidFuzz candidates."""
    if (
        len(word) < _MIN_FUZZY_WORD_LENGTH
        or not word.isalpha()
        or word in _PROTECTED_COMMON_WORDS
        or word in vocab
    ):
        return word

    matches = process.extract(
        word,
        vocab,
        scorer=fuzz.ratio,
        limit=3,
    )
    if not matches:
        return word

    best_match, best_score, _ = matches[0]
    second_score = matches[1][1] if len(matches) > 1 else 0

    if best_score < _FUZZY_SCORE_THRESHOLD:
        return word

    if best_score - second_score < _FUZZY_MARGIN_THRESHOLD:
        return word

    return best_match


def _domain_correct(text: str, domain: str | None) -> str:
    """Correct OCR noise only against the detected domain vocabulary."""
    if not domain:
        return text

    vocab = DOMAIN_VOCAB.get(domain)
    if not vocab:
        return text

    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        return _fuzzy_match(word, vocab)

    return _TOKEN_PATTERN.sub(replace, text)


# --------------------------------------------------------------------------- #
#  Step 4: Tokenization                                                        #
# --------------------------------------------------------------------------- #

def _tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens with a regex tokenizer."""
    return re.findall(r"\b\w+\b", text.lower())


# --------------------------------------------------------------------------- #
#  Step 5: Remove stopwords                                                    #
# --------------------------------------------------------------------------- #

def _remove_stopwords(tokens: list[str]) -> list[str]:
    """Remove common English stopwords for sparse lexical models."""
    stop_words = _stop_words()
    return [token for token in tokens if token.isalpha() and token not in stop_words]


# --------------------------------------------------------------------------- #
#  Step 6: Lemmatization                                                       #
# --------------------------------------------------------------------------- #

def _lemmatize(tokens: list[str]) -> list[str]:
    """Reduce tokens to their base form using spaCy's contextual lemmatizer."""
    if not tokens:
        return []

    protected_terms = _all_domain_terms()
    nlp = _get_spacy_nlp()
    doc = nlp(" ".join(tokens))
    lemmas: list[str] = []

    for token in doc:
        if not token.text.strip():
            continue

        if token.text in protected_terms:
            lemmas.append(token.text)
        elif token.lemma_.strip():
            lemmas.append(token.lemma_)

    return lemmas


# --------------------------------------------------------------------------- #
#  Public API: SBERT-first preprocessing                                       #
# --------------------------------------------------------------------------- #

def preprocess_for_sbert(text: str, debug: bool = False) -> str:
    """Primary pipeline for semantic similarity with Sentence-BERT.

    Pipeline: sanitize -> fix_split_words -> domain_correct
    """
    if debug:
        logger.debug("SBERT preprocessing input: %s...", text[:120])

    sanitized = _sanitize(text)
    split_fixed = _fix_split_words(sanitized)
    domain = _detect_domain(split_fixed)
    corrected = _domain_correct(split_fixed, domain)

    if debug:
        logger.debug("SBERT sanitized: %s...", sanitized[:120])
        logger.debug("SBERT split-word fixed: %s...", split_fixed[:120])
        logger.debug("SBERT detected domain: %s", domain or "none")
        logger.debug("SBERT ready: %s...", corrected[:120])

    return corrected


def preprocess_for_tfidf(text: str, debug: bool = False) -> str:
    """Secondary pipeline for lightweight lexical similarity.

    Pipeline: sanitize -> fix_split_words -> domain_correct -> tokenize
              -> remove_stopwords -> lemmatize
    """
    if debug:
        logger.debug("TF-IDF preprocessing input: %s...", text[:120])

    sanitized = _sanitize(text)
    split_fixed = _fix_split_words(sanitized)
    domain = _detect_domain(split_fixed)
    corrected = _domain_correct(split_fixed, domain)
    tokens = _tokenize(corrected)
    filtered_tokens = _remove_stopwords(tokens)
    lemmas = _lemmatize(filtered_tokens)
    result = " ".join(lemmas)

    if debug:
        logger.debug("TF-IDF sanitized: %s...", sanitized[:120])
        logger.debug("TF-IDF split-word fixed: %s...", split_fixed[:120])
        logger.debug("TF-IDF detected domain: %s", domain or "none")
        logger.debug("TF-IDF tokenized: %s", tokens[:20])
        logger.debug("TF-IDF stopwords removed: %s", filtered_tokens[:20])
        logger.debug("TF-IDF ready: %s...", result[:120])

    return result


# --------------------------------------------------------------------------- #
#  Markdown-aware SBERT preprocessing (for Mistral OCR output)                 #
# --------------------------------------------------------------------------- #

_MD_HEADING_RE = re.compile(r"^#{1,6}\s+")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"\*(.+?)\*")
_MD_LEADING_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_MD_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*-{2,}[\s|:-]*$")
_LATEX_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_LATEX_INLINE_RE = re.compile(r"\$(.+?)\$")
_HTML_ENTITY_RE = re.compile(r"&(gt|lt|amp|quot|apos);")

_HTML_ENTITY_MAP = {
    "gt": ">", "lt": "<", "amp": "&", "quot": '"', "apos": "'",
}


def preprocess_markdown_for_sbert(text: str) -> str:
    """Markdown-aware preprocessing that preserves case, math, and structure.

    Unlike preprocess_for_sbert, this does NOT lowercase, strip special chars,
    or run fuzzy domain correction — Mistral output is clean enough that those
    steps are net negative for SBERT.
    """
    lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()

        if _MD_TABLE_SEPARATOR_RE.match(stripped):
            continue

        stripped = _MD_HEADING_RE.sub("", stripped)
        stripped = _MD_BOLD_RE.sub(r"\1", stripped)
        stripped = _MD_ITALIC_RE.sub(r"\1", stripped)
        stripped = _MD_LEADING_BULLET_RE.sub("", stripped)

        stripped = _LATEX_DISPLAY_RE.sub(r" \1 ", stripped)
        stripped = _LATEX_INLINE_RE.sub(r" \1 ", stripped)

        def _entity_replace(m: re.Match) -> str:
            return _HTML_ENTITY_MAP.get(m.group(1), m.group(0))

        stripped = _HTML_ENTITY_RE.sub(_entity_replace, stripped)

        stripped = re.sub(r"\s+", " ", stripped).strip()
        if stripped:
            lines.append(stripped)

    return " ".join(lines)


# --------------------------------------------------------------------------- #
#  Sentence splitting                                                          #
# --------------------------------------------------------------------------- #

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_MIN_SENTENCE_TOKENS = 3


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, preferring spaCy sents with regex fallback.

    Drops sentences with fewer than _MIN_SENTENCE_TOKENS tokens to filter
    OCR noise fragments.
    """
    if not text or not text.strip():
        return []

    sentences: list[str] = []
    try:
        nlp = _get_spacy_nlp()
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
    except Exception:
        sentences = _SENTENCE_SPLIT_RE.split(text.strip())

    return [
        s for s in sentences
        if s.strip() and len(s.split()) >= _MIN_SENTENCE_TOKENS
    ]


# --------------------------------------------------------------------------- #
#  CLI quick-test                                                              #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    sample = """
    Rubernates deployment uses a hem chart and yaml template.
    The applica tion enables integra tion with postresql service and redis.
    """

    print("Original:", sample.strip())
    print()
    print("SBERT version:", preprocess_for_sbert(sample, debug=True))
    print()
    print("TF-IDF version:", preprocess_for_tfidf(sample, debug=True))
