# PROJECT STATE

## Overview

ExaminerAI is an AI-driven system for generating exam predicted questions and booklets from course documents.

## Current Milestone: MVP Refactor (Phase 1)
- Status: 🟢 IN PROGRESS
- Goal: Fix core pipeline flow, automate question generation, and integrate past paper frequency analysis.

## Accumulated Context

### Completed Todos

- [x] [Upgrade topic mapping to embedding similarity](.planning/todos/done/2026-03-24-upgrade-topic-mapping-to-embedding-similarity.md)
- [x] [Add confidence scoring to topics](.planning/todos/done/2026-03-24-add-confidence-scoring-to-topics.md)
- [x] [Implement multi-question generation per topic](.planning/todos/done/2026-03-24-implement-multi-question-generation-per-topic.md)
- [x] [Add time-based weighting for past papers](.planning/todos/done/2026-03-24-add-time-based-weighting-for-past-papers.md)
- [x] [Enable question type distribution learning](.planning/todos/done/2026-03-24-enable-question-type-distribution-learning.md)
- [x] [Implement threshold-based topic pruning](.planning/todos/done/2026-03-24-implement-threshold-based-topic-pruning.md)
- [x] [Enable relationship detection for comparative questions](.planning/todos/done/2026-03-24-enable-relationship-detection-for-comparative-questions.md)
- [x] [Calibrate confidence based on relative rank gap](.planning/todos/done/2026-03-24-calibrate-confidence-based-on-relative-rank-gap.md)
- [x] [Remove double-brain from decision logic](.planning/todos/done/2026-03-24-remove-double-brain.md)
- [x] [Fix pruning using statistical dynamic threshold](.planning/todos/done/2026-03-24-fix-pruning-using-statistics.md)
- [x] [Fix topic mapping with multi-topic soft assignment](.planning/todos/done/2026-03-24-fix-topic-mapping.md)
- [x] [Fix confidence system using score ratios](.planning/todos/done/2026-03-24-fix-confidence-system.md)
- [x] [Fix relationship detection with stricter conditions](.planning/todos/done/2026-03-24-fix-relationship-detection.md)
- [x] [Add LLM fallback for non-informative answers](.planning/todos/done/2026-03-24-add-llm-fallback.md)
- [x] [Upgrade line_metadata with density and keywords](.planning/todos/done/2026-03-24-upgrade-line-metadata.md)
- [x] [Implement evaluation system for prediction accuracy](.planning/todos/done/2026-03-24-implement-evaluation-system.md)
- [x] [Implement failure detection and explainability for topics](.planning/todos/done/2026-03-24-failure-detection-explainability.md)
- [x] [Quality checks for document size and content density](.planning/todos/done/2026-03-24-quality-checks-for-document.md)
- [x] [Final output deduplication and pipeline health](.planning/todos/done/2026-03-24-deduplication-and-health-logs.md)
- [x] [Past paper edge case extraction and topic normalization](.planning/todos/done/2026-03-24-past-paper-edge-cases.md)
- [x] [Generalization and reliability across diverse note styles](.planning/todos/done/2026-03-24-generalization-testing.md)
- [x] [Score weight calibration and note-pastpaper contradiction handling](.planning/todos/done/2026-03-24-score-calibration.md)
- [x] [Topic clustering and study-mode prioritization](.planning/todos/done/2026-03-24-clustering-and-study-mode.md)
- [x] [Noisy past paper question deduplication](.planning/todos/done/2026-03-24-past-paper-deduplication.md)

### Pending Todos

[No pending tasks. Phase 1 MVP Refactor Complete.]

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Topic-Driven Flow | Importance is central to exams. Retrieval should support, not drive, output. |
| Deterministic Marks | Marks are consistent with question types (Definition/Explanation/Discussion). |
| Stable Templates | Reduced hallucination by using template-driven question generation over raw LLM. |
