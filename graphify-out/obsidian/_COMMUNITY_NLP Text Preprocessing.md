---
type: community
cohesion: 0.11
members: 29
---

# NLP Text Preprocessing

**Cohesion:** 0.11 - loosely connected
**Members:** 29 nodes

## Members
- [[Correct OCR noise only against the detected domain vocabulary.]] - rationale - backend/core/nlp.py
- [[Decide whether two adjacent OCR tokens should be merged.]] - rationale - backend/core/nlp.py
- [[Flatten every configured domain vocabulary into a single lookup set.]] - rationale - backend/core/nlp.py
- [[Infer the text domain using lightweight exact-match heuristics.]] - rationale - backend/core/nlp.py
- [[Load the spaCy model lazily and cache it for reuse.]] - rationale - backend/core/nlp.py
- [[Merge OCR-split words while preserving surrounding punctuation.]] - rationale - backend/core/nlp.py
- [[Normalize OCR text while preserving sentence structure for SBERT.]] - rationale - backend/core/nlp.py
- [[Primary pipeline for semantic similarity with Sentence-BERT.      Pipeline sani]] - rationale - backend/core/nlp.py
- [[Reduce tokens to their base form using spaCy's contextual lemmatizer.]] - rationale - backend/core/nlp.py
- [[Remove common English stopwords for sparse lexical models.]] - rationale - backend/core/nlp.py
- [[Return a cached stopword set for lightweight lexical preprocessing.]] - rationale - backend/core/nlp.py
- [[Return a safe domain correction using the top RapidFuzz candidates.]] - rationale - backend/core/nlp.py
- [[Secondary pipeline for lightweight lexical similarity.      Pipeline sanitize -]] - rationale - backend/core/nlp.py
- [[Split text into lowercase word tokens with a regex tokenizer.]] - rationale - backend/core/nlp.py
- [[_all_domain_terms()]] - code - backend/core/nlp.py
- [[_detect_domain()]] - code - backend/core/nlp.py
- [[_domain_correct()]] - code - backend/core/nlp.py
- [[_fix_split_words()]] - code - backend/core/nlp.py
- [[_fuzzy_match()]] - code - backend/core/nlp.py
- [[_get_spacy_nlp()]] - code - backend/core/nlp.py
- [[_lemmatize()]] - code - backend/core/nlp.py
- [[_remove_stopwords()]] - code - backend/core/nlp.py
- [[_sanitize()]] - code - backend/core/nlp.py
- [[_should_merge_split()]] - code - backend/core/nlp.py
- [[_stop_words()]] - code - backend/core/nlp.py
- [[_tokenize()]] - code - backend/core/nlp.py
- [[nlp.py]] - code - backend/core/nlp.py
- [[preprocess_for_sbert()]] - code - backend/core/nlp.py
- [[preprocess_for_tfidf()]] - code - backend/core/nlp.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/NLP_Text_Preprocessing
SORT file.name ASC
```
