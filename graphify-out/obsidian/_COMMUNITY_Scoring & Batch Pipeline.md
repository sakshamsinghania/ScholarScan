---
type: community
cohesion: 0.07
members: 49
---

# Scoring & Batch Pipeline

**Cohesion:** 0.07 - loosely connected
**Members:** 49 nodes

## Members
- [[.__init__()_3]] - code - backend/core/main.py
- [[.batch_compute()]] - code - backend/core/similarity.py
- [[.compute()_1]] - code - backend/core/similarity.py
- [[.compute()_2]] - code - backend/tests/test_similarity.py
- [[.embed()]] - code - backend/core/similarity.py
- [[.summary()]] - code - backend/core/scoring.py
- [[.test_falls_back_to_tfidf_when_sbert_is_unavailable()]] - code - backend/tests/test_similarity.py
- [[.test_marks_model_unavailable_when_local_load_fails()]] - code - backend/tests/test_similarity.py
- [[.test_resolves_sentence_transformers_cache_alias()]] - code - backend/tests/test_similarity.py
- [[A single grade band definition.]] - rationale - backend/core/scoring.py
- [[AssessmentResult]] - code - backend/core/scoring.py
- [[BatchConfig]] - code - backend/core/main.py
- [[Compute semantic similarity between student and model text.          Returns a s]] - rationale - backend/core/similarity.py
- [[Computes semantic similarity using Sentence-BERT embeddings.      Accepts text p]] - rationale - backend/core/similarity.py
- [[Configuration for batch assessment processing.      Attributes         model_an]] - rationale - backend/core/main.py
- [[Convert a grade band to a numeric mark.      Applies a small keyword-coverage pe]] - rationale - backend/core/scoring.py
- [[Extract (student_id, question_id) from filenames like        student_01_Q1.jpg]] - rationale - backend/core/main.py
- [[Fill in the feedback template with missing keywords and overlap ratio.      Args]] - rationale - backend/core/scoring.py
- [[Find the grade band matching a combined similarity score.]] - rationale - backend/core/scoring.py
- [[Immutable result for one student's answer assessment.]] - rationale - backend/core/scoring.py
- [[NamedTuple]] - code
- [[Normalize text through the full core pipeline before similarity.      Data flow]] - rationale - backend/core/main.py
- [[Pretty-print summary for CLI  Colab output.]] - rationale - backend/core/scoring.py
- [[Print class-level summary statistics after all papers are graded.]] - rationale - backend/core/main.py
- [[Return the sentence embedding vector for a given text.]] - rationale - backend/core/similarity.py
- [[Run batch assessment on all images in the configured folder.]] - rationale - backend/core/main.py
- [[Run the full assessment pipeline for one student answer image.      Args]] - rationale - backend/core/main.py
- [[SBERTSimilarity]] - code - backend/core/similarity.py
- [[Score a batch of student answers against ONE model answer.          Much faster]] - rationale - backend/core/similarity.py
- [[Take the output of compute_similarity() and produce a full AssessmentResult.]] - rationale - backend/core/scoring.py
- [[TestComputeSimilarityFallback]] - code - backend/tests/test_similarity.py
- [[TestSBERTSimilarityFallback]] - code - backend/tests/test_similarity.py
- [[Tests for similarity scoring and offline SBERT fallback behavior.]] - rationale - backend/tests/test_similarity.py
- [[Write all assessment results to a CSV file.      Columns       student_id, ques]] - rationale - backend/core/main.py
- [[_GradeBand]] - code - backend/core/scoring.py
- [[_UnavailableSBERT]] - code - backend/tests/test_similarity.py
- [[_compute_marks()]] - code - backend/core/scoring.py
- [[_export_csv()]] - code - backend/core/main.py
- [[_find_band()]] - code - backend/core/scoring.py
- [[_generate_feedback()]] - code - backend/core/scoring.py
- [[_parse_filename()]] - code - backend/core/main.py
- [[_prepare_similarity_inputs()]] - code - backend/core/main.py
- [[_print_summary()]] - code - backend/core/main.py
- [[main()]] - code - backend/core/main.py
- [[main.py]] - code - backend/core/main.py
- [[process_single()]] - code - backend/core/main.py
- [[score_answer()]] - code - backend/core/scoring.py
- [[scoring.py]] - code - backend/core/scoring.py
- [[test_similarity.py]] - code - backend/tests/test_similarity.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Scoring_&_Batch_Pipeline
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_App Bootstrap & Services]]
- 3 edges to [[_COMMUNITY_Similarity Engine]]

## Top bridge nodes
- [[SBERTSimilarity]] - degree 27, connects to 2 communities
- [[.compute()_1]] - degree 4, connects to 1 community