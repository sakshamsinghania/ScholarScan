# =============================================================================
# structure_extractor.py — Semantic Cleaning & Structure Extraction
# =============================================================================
# Pipeline position:
#   OCR → nlp.py (preprocess_for_sbert) → structure_extractor → SBERT → Scoring
#
# Takes cleaned OCR text and produces a structured dictionary with:
#   - student_info (name, roll_no)
#   - questions (number, question text, answer text, answer_points)
#
# Dependencies: re, logging (stdlib only — no ML)
# =============================================================================

from __future__ import annotations

import logging
import re
from typing import Any

__all__ = ["extract_structure", "semantic_clean", "structure_to_text"]

logger = logging.getLogger(__name__)


# =========================================================================== #
#  PART 1: SEMANTIC CLEANING LAYER                                            #
# =========================================================================== #

# --------------------------------------------------------------------------- #
#  1a. Normalize answer keywords                                               #
# --------------------------------------------------------------------------- #

_ANS_PATTERN = re.compile(
    r"\b(an['`\u2019]s|ans\.?|answer)\s*[:\-\u2192\u2013\u2014=>\.]?\s*",
    re.IGNORECASE,
)


def normalize_answer_keywords(text: str) -> str:
    """Normalize answer markers like 'ans', 'an's', 'ans.' into 'Ans ->'."""
    return _ANS_PATTERN.sub("Ans -> ", text)


# --------------------------------------------------------------------------- #
#  1b. Fix common OCR semantic errors                                          #
# --------------------------------------------------------------------------- #

# Map of OCR-garbled words to correct forms.
# Only include high-confidence, unambiguous corrections.
_OCR_ERROR_MAP: dict[str, str] = {
    # Structural/general
    "comportadata": "components",
    "componets": "components",
    "compnents": "components",
    "componants": "components",
    "integratin": "integration",
    "intergration": "integration",
    "configuraton": "configuration",
    "configration": "configuration",
    "deployement": "deployment",
    "deploment": "deployment",
    "managment": "management",
    "manegement": "management",
    "dependancy": "dependency",
    "dependecies": "dependencies",
    "dependancies": "dependencies",
    "discription": "description",
    "decription": "description",
    "defination": "definition",
    "definations": "definitions",
    "defnition": "definition",
    "defnitions": "definitions",
    "paramaters": "parameters",
    "parametrs": "parameters",
    "architecure": "architecture",
    "architeture": "architecture",
    "architectur": "architecture",
    "applicaton": "application",
    "aplication": "application",
    "enviroment": "environment",
    "envirnoment": "environment",
    "environement": "environment",
    "infrastucture": "infrastructure",
    "infrastruture": "infrastructure",
    "repostory": "repository",
    "repositry": "repository",
    "repositary": "repository",
    "resourse": "resource",
    "resourses": "resources",
    "resoures": "resources",
    # Cloud/K8s domain
    "yami": "yaml",
    "yame": "yaml",
    "yamal": "yaml",
    "hem": "helm",
    "kubernates": "kubernetes",
    "kubernets": "kubernetes",
    "kuberntes": "kubernetes",
    "kuberentes": "kubernetes",
    "rubernates": "kubernetes",
    "orchastration": "orchestration",
    "orchestation": "orchestration",
    "contaner": "container",
    "contanier": "container",
    "contianer": "container",
    "microservies": "microservices",
    "mircoservices": "microservices",
    "persistant": "persistent",
    "persistance": "persistence",
    "serverles": "serverless",
    "templete": "template",
    "templat": "template",
    "tempalte": "template",
    "postresql": "postgresql",
    "resouce": "resource",
    "registery": "registry",
    "registary": "registry",
    # IMPROVEMENT: additional high-confidence OCR corrections
    "exection": "execution",
    "exicution": "execution",
    "availabe": "available",
    "availible": "available",
    "scalabe": "scalable",
    "scaleble": "scalable",
    "overead": "overhead",
    "overhed": "overhead",
    "netwrok": "network",
    "nework": "network",
    "securty": "security",
    "secuirty": "security",
    "protocl": "protocol",
    "protcol": "protocol",
    "algorythm": "algorithm",
    "algoritm": "algorithm",
    "performace": "performance",
    "perfomance": "performance",
    "autentication": "authentication",
    "authentcation": "authentication",
    "authorizaton": "authorization",
    "monitorng": "monitoring",
    "monotoring": "monitoring",
}

# Build a regex pattern that matches any OCR error word (longest first)
_OCR_ERRORS_SORTED = sorted(_OCR_ERROR_MAP.keys(), key=len, reverse=True)
_OCR_ERROR_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _OCR_ERRORS_SORTED) + r")\b",
    re.IGNORECASE,
)


def fix_common_ocr_errors(text: str) -> str:
    """Replace known OCR-garbled words with their correct forms."""
    def _replace(match: re.Match[str]) -> str:
        word = match.group(0)
        correction = _OCR_ERROR_MAP.get(word.lower())
        if correction is None:
            return word
        # Preserve title-case if the original was capitalized
        if word[0].isupper():
            return correction.capitalize()
        return correction

    return _OCR_ERROR_PATTERN.sub(_replace, text)


# --------------------------------------------------------------------------- #
#  1c. Normalize technical terms                                               #
# --------------------------------------------------------------------------- #

# Canonical lowercase forms for common technical terms
_TECH_TERM_MAP: dict[str, str] = {
    "yaml": "YAML",
    "json": "JSON",
    "api": "API",
    "apis": "APIs",
    "http": "HTTP",
    "https": "HTTPS",
    "sql": "SQL",
    "nosql": "NoSQL",
    "tcp": "TCP",
    "udp": "UDP",
    "dns": "DNS",
    "ssh": "SSH",
    "ssl": "SSL",
    "tls": "TLS",
    "url": "URL",
    "uri": "URI",
    "html": "HTML",
    "css": "CSS",
    "xml": "XML",
    "sdk": "SDK",
    "cli": "CLI",
    "gui": "GUI",
    "crd": "CRD",
    "crds": "CRDs",
    "ci/cd": "CI/CD",
    "ci": "CI",
    "cd": "CD",
    "kubernetes": "Kubernetes",
    "k8s": "K8s",
    "docker": "Docker",
    "helm": "Helm",
    "redis": "Redis",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mongodb": "MongoDB",
    "nginx": "Nginx",
    "linux": "Linux",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "devops": "DevOps",
    "github": "GitHub",
    "gitlab": "GitLab",
}

_TECH_TERM_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_TECH_TERM_MAP, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def normalize_technical_terms(text: str) -> str:
    """Normalize technical terms to their canonical casing."""
    def _replace(match: re.Match[str]) -> str:
        return _TECH_TERM_MAP.get(match.group(0).lower(), match.group(0))

    return _TECH_TERM_PATTERN.sub(_replace, text)


# --------------------------------------------------------------------------- #
#  1d. Merge broken phrases                                                    #
# --------------------------------------------------------------------------- #

# Compound terms that OCR often splits with spaces or hyphens
_COMPOUND_TERMS: dict[str, str] = {
    "go template": "go-template",
    "go - template": "go-template",
    "go-template": "go-template",
    "post install": "post-install",
    "post - install": "post-install",
    "pre install": "pre-install",
    "pre - install": "pre-install",
    "sub chart": "sub-chart",
    "sub - chart": "sub-chart",
    "re deploy": "re-deploy",
    "re - deploy": "re-deploy",
    "roll back": "rollback",
    "name space": "namespace",
    "name - space": "namespace",
    "load balancer": "load-balancer",
    "load - balancer": "load-balancer",
    "auto scale": "auto-scale",
    "auto scaling": "auto-scaling",
    "auto - scaling": "auto-scaling",
    "health check": "health-check",
    "health - check": "health-check",
    "read write": "read-write",
    "read - write": "read-write",
    "real time": "real-time",
    "real - time": "real-time",
    "open source": "open-source",
    "open - source": "open-source",
    "end point": "endpoint",
    "end - point": "endpoint",
    "data base": "database",
    "data - base": "database",
    "work load": "workload",
    "work - load": "workload",
    "work flow": "workflow",
    "work - flow": "workflow",
    "micro service": "microservice",
    "micro - service": "microservice",
}

# Sort by length (longest first) to match multi-word compounds before substrings
_COMPOUND_SORTED = sorted(_COMPOUND_TERMS.keys(), key=len, reverse=True)
_COMPOUND_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _COMPOUND_SORTED) + r")\b",
    re.IGNORECASE,
)


def merge_broken_phrases(text: str) -> str:
    """Merge OCR-split compound terms into their correct form."""
    def _replace(match: re.Match[str]) -> str:
        return _COMPOUND_TERMS.get(match.group(0).lower(), match.group(0))

    return _COMPOUND_PATTERN.sub(_replace, text)


# --------------------------------------------------------------------------- #
#  1e. Clean noise words                                                       #
# --------------------------------------------------------------------------- #


def clean_noise(text: str) -> str:
    """Remove irrelevant metadata tokens that add no semantic value."""
    # Remove noise keywords from the header portion
    # Only clean the part before the first question marker to avoid damaging answers
    first_q_match = re.search(r"\b\d+\s*[\.\):]", text)
    if first_q_match:
        header = text[:first_q_match.start()]
        body = text[first_q_match.start():]

        # Remove common noise keywords from header
        header = re.sub(
            r"\b(date|assignment|semester|section|spiral|"
            r"subject\s*code|examination|max\.?\s*marks|time\s*allowed)\b"
            r"\s*[:;\-]?\s*",
            " ",
            header,
            flags=re.IGNORECASE,
        )
        text = header + body

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# --------------------------------------------------------------------------- #
#  1f. Normalize punctuation                                                   #
# --------------------------------------------------------------------------- #

def _normalize_punctuation(text: str) -> str:
    """Ensure proper spacing around punctuation."""
    # Space after punctuation if missing (but not inside numbers like 2.3)
    text = re.sub(r"([,;:])(?=[^\s\d])", r"\1 ", text)
    # Remove space before punctuation
    text = re.sub(r"\s+([,;:\.!?])", r"\1", text)
    # Normalize arrow-like separators
    text = re.sub(r"\s*[-=]+>\s*", " -> ", text)
    text = re.sub(r"\s*\u2192\s*", " -> ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


# --------------------------------------------------------------------------- #
#  1g. Safe capitalization (IMPROVEMENT: preserves tech terms)                  #
# --------------------------------------------------------------------------- #

# Words that must NOT be lowered by .capitalize() — their canonical form is set
# by normalize_technical_terms() and must survive later formatting passes.
_PRESERVE_CASE_PREFIXES = frozenset(
    list(_TECH_TERM_MAP.values()) + list(_TECH_TERM_MAP.keys())
)


def _safe_capitalize(text: str) -> str:
    """Capitalize the first letter of *text* without clobbering tech terms.

    Standard str.capitalize() lower-cases everything after the first char,
    which would turn 'Kubernetes' into 'kubernetes'.  This version only
    touches the very first character.
    """
    if not text:
        return text
    # Skip if the text already starts with an uppercase or a tech term
    if text[0].isupper():
        return text
    return text[0].upper() + text[1:]


# --------------------------------------------------------------------------- #
#  1h. Filename / resource-name normalization (IMPROVEMENT)                     #
# --------------------------------------------------------------------------- #

_FILENAME_NORM_MAP: dict[str, str] = {
    "chart.yaml": "Chart.yaml",
    "chart.yml": "Chart.yml",
    "values.yaml": "values.yaml",
    "values.yml": "values.yml",
    "notes.txt": "NOTES.txt",
    "readme.md": "README.md",
    "license": "LICENSE",
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "jenkinsfile": "Jenkinsfile",
}

_FILENAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_FILENAME_NORM_MAP, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _normalize_filenames(text: str) -> str:
    """Normalize well-known file and resource names to canonical casing."""
    def _replace(match: re.Match[str]) -> str:
        return _FILENAME_NORM_MAP.get(match.group(0).lower(), match.group(0))
    return _FILENAME_PATTERN.sub(_replace, text)


# --------------------------------------------------------------------------- #
#  1i. Combined semantic cleaning pipeline                                     #
# --------------------------------------------------------------------------- #

def semantic_clean(text: str, debug: bool = False) -> str:
    """Run the full semantic cleaning pipeline on pre-cleaned OCR text.

    Pipeline order:
      1. Normalize answer keywords
      2. Fix common OCR errors
      3. Merge broken phrases
      4. Clean noise words
      5. Normalize technical terms
      6. Normalize file/resource names
      7. Normalize punctuation

    Args:
        text: Cleaned text from nlp.py (preprocess_for_sbert output).
        debug: If True, log each intermediate step.

    Returns:
        Semantically cleaned text ready for structure extraction.
    """
    if not text or not text.strip():
        return ""

    if debug:
        logger.debug("Semantic clean input: %s...", text[:150])

    text = normalize_answer_keywords(text)
    if debug:
        logger.debug("After answer keyword normalization: %s...", text[:150])

    text = fix_common_ocr_errors(text)
    if debug:
        logger.debug("After OCR error fixes: %s...", text[:150])

    text = merge_broken_phrases(text)
    if debug:
        logger.debug("After broken phrase merge: %s...", text[:150])

    text = clean_noise(text)
    if debug:
        logger.debug("After noise cleaning: %s...", text[:150])

    text = normalize_technical_terms(text)
    if debug:
        logger.debug("After technical term normalization: %s...", text[:150])

    text = _normalize_filenames(text)  # IMPROVEMENT: canonical file names
    if debug:
        logger.debug("After filename normalization: %s...", text[:150])

    text = _normalize_punctuation(text)
    if debug:
        logger.debug("Semantic clean output: %s...", text[:150])

    return text


# =========================================================================== #
#  PART 2: STRUCTURE EXTRACTION LAYER                                         #
# =========================================================================== #

# --------------------------------------------------------------------------- #
#  2a. Extract student info                                                    #
# --------------------------------------------------------------------------- #

_NAME_PATTERN = re.compile(
    r"\bname\s*[-:;\s]+\s*([a-zA-Z][a-zA-Z\s\.]{1,40}?)(?=\s*(?:roll|rou|rol|reg|enroll|class|section|\d{5,}|\b[a-z]{2,}\s*no))",
    re.IGNORECASE,
)
_NAME_FALLBACK_PATTERN = re.compile(
    r"\bname\s*[-:;\s]+\s*([a-zA-Z][a-zA-Z\s\.]{1,40}?)(?=\s{2,}|\s*$|\s*\d+\s*[\.\)])",
    re.IGNORECASE,
)

_ROLL_PATTERN = re.compile(
    r"\b(?:roll|rou|rol|reg(?:istration)?|enroll(?:ment)?)\s*(?:no|number|num)?\.?\s*[-:;\s]*\s*"
    r"([a-zA-Z]?\d[\w\-/]{4,20})",
    re.IGNORECASE,
)


def extract_student_info(text: str) -> dict[str, str | None]:
    """Extract student name and roll number from text.

    Handles OCR variants like 'rou no', 'roll no', etc.

    Returns:
        {"name": str | None, "roll_no": str | None}
    """
    # Extract name
    name = None
    name_match = _NAME_PATTERN.search(text) or _NAME_FALLBACK_PATTERN.search(text)
    if name_match:
        raw_name = name_match.group(1).strip()
        # Clean up: remove trailing noise, title-case it
        raw_name = re.sub(r"\s+", " ", raw_name).strip()
        raw_name = re.sub(r"[^a-zA-Z\s\.]", "", raw_name).strip()
        if raw_name and len(raw_name) > 1:
            name = raw_name.title()

    # Extract roll number
    roll_no = None
    roll_match = _ROLL_PATTERN.search(text)
    if roll_match:
        roll_no = roll_match.group(1).strip()

    return {"name": name, "roll_no": roll_no}


# --------------------------------------------------------------------------- #
#  2b. Split text into question blocks                                         #
# --------------------------------------------------------------------------- #

# Matches question number patterns: "1.", "1)", "1:", "Q1.", "Q.1", "q1"
_QUESTION_SPLIT_PATTERN = re.compile(
    r"(?:^|\s)(?:q\.?\s*)?(\d{1,2})\s*[\.\)\:\-]\s*",
    re.IGNORECASE,
)


def split_questions(text: str) -> list[dict[str, Any]]:
    """Split the text body into question blocks.

    Each block contains the question number and the raw text
    (which includes both the question and the answer).

    Returns:
        List of {"question_number": int, "raw_block": str}
    """
    # Find all question number markers
    matches = list(_QUESTION_SPLIT_PATTERN.finditer(text))

    if not matches:
        # Fallback: treat entire text as a single block
        return [{"question_number": 1, "raw_block": text.strip()}]

    blocks: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        q_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_block = text[start:end].strip()

        if raw_block:
            blocks.append({"question_number": q_num, "raw_block": raw_block})

    return blocks


# --------------------------------------------------------------------------- #
#  2c. Extract answer from a question block                                    #
# --------------------------------------------------------------------------- #

_ANS_MARKER_PATTERN = re.compile(
    r"\bAns\s*->\s*",
    re.IGNORECASE,
)


def extract_answer_block(question_block: str) -> tuple[str, str]:
    """Separate question text from answer text within a question block.

    Args:
        question_block: Raw text containing both question and answer.

    Returns:
        (question_text, answer_text) tuple.
        If no answer marker found, question_text is empty and
        the entire block is treated as the answer.
    """
    ans_match = _ANS_MARKER_PATTERN.search(question_block)

    if ans_match:
        question_text = question_block[:ans_match.start()].strip()
        answer_text = question_block[ans_match.end():].strip()
        return question_text, answer_text

    # Fallback: no explicit answer marker.
    # Check if the block starts with a question-like sentence (ends with ?)
    q_mark = question_block.find("?")
    if q_mark != -1:
        question_text = question_block[:q_mark + 1].strip()
        answer_text = question_block[q_mark + 1:].strip()
        return question_text, answer_text

    # No clear separation: treat entire block as answer, no question text
    return "", question_block.strip()


# --------------------------------------------------------------------------- #
#  2d. Extract answer points from answer text                                  #
# --------------------------------------------------------------------------- #

# Bullet patterns on their own lines: "- ", "* ", "• ", "a)", "i."
_BULLET_NEWLINE_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:[-*\u2022\u25CF\u25CB\u2023]|[a-z]\)|[ivxIVX]+[\.\)]|"
    r"\d+\.\d+[\.\)]?)\s+",
)

# Named inline items: " - filename.ext - description" or " - dirname/ - description"
# Detects file-like names (contain dot or end with slash) preceded by a bullet dash,
# followed by a separator dash. Splits keep name + description together.
_NAMED_INLINE_ITEM_PATTERN = re.compile(
    r"\s+-\s+([\w][\w\.\-]*(?:\.\w+|/))\s*[-\u2013\u2014]\s+",
)

# Simple inline bullet pattern (fallback): handles ` - item` within a single line
_INLINE_BULLET_PATTERN = re.compile(
    r"\s+-\s+(?=[a-zA-Z][\w\.\-/]*[\s\-:])",
)

# Named list items on their own lines like "Chart.yaml -", "values.yaml -"
_NAMED_ITEM_PATTERN = re.compile(
    r"(?:^|\s)([a-zA-Z][\w\.\-]*(?:/[\w]*)?)\s*[-\u2013\u2014]\s+(?=[a-zA-Z])",
)

# Sentence split for fallback — handles lowercase text from OCR pipeline
_SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?])\s+(?=[a-zA-Z])"
)


def extract_answer_points(answer_text: str) -> list[str]:
    """Break answer text into individual points/bullets.

    Detection priority:
      1. Explicit newline bullets (-, *, bullet chars at line start)
      2. Named inline items (" - file.ext - description" pattern)
      3. Simple inline bullets (" - item - item" pattern)
      4. Named items on own lines
      5. Sentence-level splitting (fallback)

    Args:
        answer_text: The raw answer portion of a question block.

    Returns:
        List of answer point strings. If no structure found,
        returns the full answer as a single item.
    """
    if not answer_text or not answer_text.strip():
        return []

    answer_text = answer_text.strip()

    # Strategy 1: Explicit newline bullet markers
    bullet_matches = list(_BULLET_NEWLINE_PATTERN.finditer(answer_text))
    if len(bullet_matches) >= 2:
        return _split_by_matches(answer_text, bullet_matches)

    # Strategy 2: Named inline items (" - chart.yaml - metadata")
    # These have file-like names (with dots or trailing slash) so we can
    # reliably pair the name with its description.
    named_inline = list(_NAMED_INLINE_ITEM_PATTERN.finditer(answer_text))
    if len(named_inline) >= 2:
        return _split_named_inline_items(answer_text, named_inline)

    # Strategy 3: Simple inline bullets
    inline_matches = list(_INLINE_BULLET_PATTERN.finditer(answer_text))
    if len(inline_matches) >= 2:
        return _split_inline_bullets(answer_text, inline_matches)

    # Strategy 4: Named items on own lines
    named_matches = list(_NAMED_ITEM_PATTERN.finditer(answer_text))
    if len(named_matches) >= 2:
        return _split_by_matches(answer_text, named_matches, include_match=True)

    # Strategy 5: Sentence splitting (works on lowercase OCR text)
    sentences = _SENTENCE_SPLIT_PATTERN.split(answer_text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    if len(sentences) >= 2:
        return sentences

    # No structure detected — return entire answer as one point
    return [answer_text]


def _split_named_inline_items(
    text: str,
    matches: list[re.Match[str]],
) -> list[str]:
    """Split text at named inline item positions.

    Each match captures " - name.ext - " and we split so that
    "name.ext - description" stays together as one point.

    Example input:
      "preamble text - chart.yaml - metadata desc - values.yaml - config desc"
    Output:
      ["preamble text", "chart.yaml - metadata desc", "values.yaml - config desc"]
    """
    points: list[str] = []

    # Preamble: text before the first named item's leading " - "
    preamble = text[:matches[0].start()].strip()
    if preamble and len(preamble) > 15:
        points.append(preamble)

    for i, match in enumerate(matches):
        # The point starts at the filename (group 1 start)
        name_start = match.start(1)
        # The point ends at the start of the next match's leading " - "
        if i + 1 < len(matches):
            point_end = matches[i + 1].start()
        else:
            point_end = len(text)

        point = text[name_start:point_end].strip()
        # Clean trailing dash if any
        point = re.sub(r"\s*-\s*$", "", point).strip()
        if point:
            points.append(point)

    return points


def _split_inline_bullets(
    text: str,
    matches: list[re.Match[str]],
) -> list[str]:
    """Split text at inline bullet positions (' - ') into points.

    Preserves preamble text before the first bullet and ensures
    flow content (arrows like ' -> ') is not broken.
    """
    points: list[str] = []

    # Preamble: text before the first inline bullet
    preamble = text[:matches[0].start()].strip()
    if preamble and len(preamble) > 15:
        points.append(preamble)

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        point = text[start:end].strip()
        if point:
            points.append(point)

    return points


def _split_by_matches(
    text: str,
    matches: list[re.Match[str]],
    include_match: bool = False,
) -> list[str]:
    """Split text at match positions into a list of points.

    Args:
        text: Full answer text.
        matches: Regex match objects marking split positions.
        include_match: If True, include the matched text in the point.

    Returns:
        List of point strings.
    """
    points: list[str] = []

    # Text before first match (preamble) — include if substantial
    preamble = text[:matches[0].start()].strip()
    if preamble and len(preamble) > 15:
        points.append(preamble)

    for i, match in enumerate(matches):
        start = match.start() if include_match else match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        point = text[start:end].strip()

        # Clean leading bullet characters
        if not include_match:
            point = re.sub(r"^[-*\u2022\u25CF\u25CB\u2023]\s*", "", point)

        if point:
            points.append(point)

    return points


# --------------------------------------------------------------------------- #
#  2d-ii. Preamble sentence splitting (IMPROVEMENT)                            #
# --------------------------------------------------------------------------- #

_PREAMBLE_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[a-zA-Z])")

# Minimum length for a split sentence to be kept as its own point
_MIN_SENTENCE_LEN = 20


def _split_preamble_sentences(points: list[str]) -> list[str]:
    """Split long preamble paragraphs into individual sentences.

    Only applies to points that look like multi-sentence prose (no
    file-like names or bullet structure).  Bullet points like
    'Chart.yaml – metadata' are left intact.
    """
    result: list[str] = []
    for point in points:
        # Skip short points or structured bullet points (contain ' – ' or ' - ' with filenames)
        if len(point) < 60 or re.search(r"\w+\.\w+\s*[-\u2013]", point):
            result.append(point)
            continue

        # Try sentence split
        sentences = _PREAMBLE_SENTENCE_SPLIT.split(point)
        meaningful = [s.strip() for s in sentences if len(s.strip()) >= _MIN_SENTENCE_LEN]

        if len(meaningful) >= 2:
            result.extend(meaningful)
        else:
            result.append(point)

    return result


# --------------------------------------------------------------------------- #
#  2d-iii. Answer point cleanup (IMPROVEMENT)                                  #
# --------------------------------------------------------------------------- #

def _clean_points(points: list[str]) -> list[str]:
    """Deduplicate, strip, remove empties, and normalize dash formatting."""
    seen: set[str] = set()
    cleaned: list[str] = []

    for point in points:
        # Strip whitespace
        point = point.strip()
        if not point:
            continue

        # Normalize separator dashes to en-dash for readability
        # Only in structured points like "Chart.yaml - metadata"
        point = re.sub(r"(\w)\s+-\s+(\w)", "\\1 \u2013 \\2", point, count=1)

        # Remove trailing punctuation noise (stray dashes, colons)
        point = re.sub(r"[\s\-:,;]+$", "", point)

        # Deduplicate (case-insensitive)
        key = point.lower()
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(point)

    return cleaned


# --------------------------------------------------------------------------- #
#  2e. Structure flow content                                                  #
# --------------------------------------------------------------------------- #

_FLOW_PATTERN = re.compile(
    r"[\w\.\-/]+(?:\s*\+\s*[\w\.\-/]+)*\s*->\s*[\w\.\-/\s]+(?:\s*->\s*[\w\.\-/\s]+)*"
)


def _preserve_flow_content(text: str) -> str:
    """Ensure pipeline/flow notation (a + b -> c -> d) is not broken.

    This is a protective pass — it ensures flow arrows and '+' connectors
    stay intact within answer points.
    """
    # Flow content is already preserved by the pipeline since we don't
    # split on '->' within answer text. This function serves as a
    # validation/normalization pass.
    text = re.sub(r"\s*->\s*", " -> ", text)
    text = re.sub(r"\s*\+\s*", " + ", text)
    return text


# =========================================================================== #
#  MAIN EXTRACTION PIPELINE                                                   #
# =========================================================================== #

def extract_structure(text: str, debug: bool = False) -> dict[str, Any]:
    """Extract structured data from cleaned OCR text.

    Full pipeline:
      1. Semantic cleaning (OCR fixes, normalization)
      2. Student info extraction (name, roll_no)
      3. Question splitting
      4. Answer extraction and point decomposition

    Args:
        text: Cleaned text from nlp.py's preprocess_for_sbert().
        debug: If True, log intermediate steps.

    Returns:
        Structured dictionary:
        {
            "student_info": {"name": str|None, "roll_no": str|None},
            "questions": [
                {
                    "question_number": int,
                    "question": str,
                    "answer": str,
                    "answer_points": [str, ...]
                },
                ...
            ]
        }
    """
    if not text or not text.strip():
        logger.warning("Empty text provided to extract_structure")
        return {"student_info": {"name": None, "roll_no": None}, "questions": []}

    # === Step 1: Semantic cleaning ===
    cleaned = semantic_clean(text, debug=debug)
    if debug:
        logger.debug("Post-semantic-clean text: %s...", cleaned[:200])

    # === Step 2: Extract student info ===
    student_info = extract_student_info(cleaned)
    if debug:
        logger.debug("Extracted student info: %s", student_info)

    # === Step 3: Remove student info portion from text for question parsing ===
    # Find where the actual content starts (after name/roll info)
    body = _strip_header(cleaned)
    if debug:
        logger.debug("Body text after header strip: %s...", body[:200])

    # === Step 4: Split into question blocks ===
    question_blocks = split_questions(body)
    if debug:
        logger.debug("Found %d question block(s)", len(question_blocks))

    # === Step 5: Extract answers and points from each block ===
    questions: list[dict[str, Any]] = []

    for block in question_blocks:
        q_num = block["question_number"]
        raw_block = block["raw_block"]

        question_text, answer_text = extract_answer_block(raw_block)

        # IMPROVEMENT: capitalize question and answer first letters safely
        question_text = _safe_capitalize(question_text)
        answer_text = _preserve_flow_content(answer_text)
        answer_text = _safe_capitalize(answer_text)

        # Extract structured points
        answer_points = extract_answer_points(answer_text)

        # IMPROVEMENT: split long preamble paragraphs into sentences
        answer_points = _split_preamble_sentences(answer_points)

        # IMPROVEMENT: deduplicate, strip, normalize dashes
        answer_points = _clean_points(answer_points)

        questions.append({
            "question_number": q_num,
            "question": question_text,
            "answer": answer_text,
            "answer_points": answer_points,
        })

        if debug:
            logger.debug(
                "Q%d: question=%s... | answer=%s... | %d points",
                q_num,
                question_text[:60],
                answer_text[:60],
                len(answer_points),
            )

    result: dict[str, Any] = {
        "student_info": student_info,
        "questions": questions,
    }

    return result


def structure_to_text(structure: dict[str, Any], debug: bool = False) -> str:
    """Flatten structured extraction output into similarity-ready answer text.

    This bridges the structure-extraction stage with the downstream
    similarity modules, while keeping `extract_structure()` focused on
    returning a structured dictionary.

    Priority per question block:
      1. `answer_points` joined in order
      2. raw `answer`
      3. `question` text as a last-resort fallback
    """
    questions = structure.get("questions", [])
    chunks: list[str] = []

    for question in questions:
        answer_points = [
            point.strip()
            for point in question.get("answer_points", [])
            if isinstance(point, str) and point.strip()
        ]

        if answer_points:
            chunks.append(". ".join(answer_points))
            continue

        answer_text = question.get("answer", "")
        if isinstance(answer_text, str) and answer_text.strip():
            chunks.append(answer_text.strip())
            continue

        question_text = question.get("question", "")
        if isinstance(question_text, str) and question_text.strip():
            chunks.append(question_text.strip())

    flattened = re.sub(r"\s+", " ", " ".join(chunks)).strip()

    if debug:
        logger.debug("Flattened structure for similarity: %s...", flattened[:200])

    return flattened


# --------------------------------------------------------------------------- #
#  Helper: strip header/metadata from body text                                #
# --------------------------------------------------------------------------- #

def _strip_header(text: str) -> str:
    """Remove the student info header from the text, returning the body.

    Tries to find where the first question or answer begins and
    returns everything from that point onward.
    """
    # Look for the first question-number marker
    q_match = re.search(r"(?:^|\s)(?:q\.?\s*)?\d{1,2}\s*[\.\)\:\-]", text, re.IGNORECASE)
    if q_match:
        return text[q_match.start():].strip()

    # Look for the first answer marker
    ans_match = re.search(r"\bAns\s*->", text, re.IGNORECASE)
    if ans_match:
        return text[ans_match.start():].strip()

    # Fallback: try to skip the first "line" (up to the first sentence break)
    # that looks like header metadata
    header_end = re.search(
        r"(?:cloud\s*computing|computer\s*science|assignment|examination)\s+",
        text,
        re.IGNORECASE,
    )
    if header_end:
        return text[header_end.end():].strip()

    return text


# =========================================================================== #
#  CLI QUICK TEST                                                             #
# =========================================================================== #

if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    sample_input = (
        "name - leeya rou no-23293916004 cloud computing assignment date "
        "1. explain the architecture of a helm chart, including its main componets. "
        "ans. a helm chart is a packaged kubernates applicaton. it contains all the "
        "resource defnitions needed to deploy an applicaton on kubernates. "
        "- chart.yami - metadata: name, version, discription "
        "- values.yami - default configuraton parametrs (overridable at deploy time) "
        "- templates/ - go - template kubernates yami files "
        "- charts/ - sub chart dependancies (e.g. redis, postgresql) "
        "- crds/ - custom resouce definations "
        "- notes.txt - post install instructions "
        "the helm engine processes: values.yami + templates -> helm engine -> kubernates yami "
        "2. what is serverles computing? explain its advantages. "
        "an's serverles computing is a cloud execution model where the cloud provider "
        "manages the infrastucture. the provider dynamically allocates resourses. "
        "advantages include: reduced cost. automatic auto - scaling. faster deployement. "
        "no server managment overhead."
    )

    print("=" * 70)
    print("  SAMPLE INPUT")
    print("=" * 70)
    print(sample_input)
    print()

    result = extract_structure(sample_input, debug=True)

    print()
    print("=" * 70)
    print("  STRUCTURED OUTPUT")
    print("=" * 70)
    print(json.dumps(result, indent=2, ensure_ascii=False))
