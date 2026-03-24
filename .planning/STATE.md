# PROJECT STATE

## Overview

ExaminerAI is an AI-driven system for generating exam predicted questions and booklets from course documents.

## Current Milestone: MVP Refactor (Phase 1)
- Status: 🟢 IN PROGRESS
- Goal: Fix core pipeline flow, automate question generation, and integrate past paper frequency analysis.

## Accumulated Context

### Pending Todos

- [ ] [Upgrade topic mapping to embedding similarity](.planning/todos/pending/2026-03-24-upgrade-topic-mapping-to-embedding-similarity.md)
- [ ] [Add confidence scoring to topics](.planning/todos/pending/2026-03-24-add-confidence-scoring-to-topics.md)
- [ ] [Implement multi-question generation per topic](.planning/todos/pending/2026-03-24-implement-multi-question-generation-per-topic.md)
- [ ] [Add time-based weighting for past papers](.planning/todos/pending/2026-03-24-add-time-based-weighting-for-past-papers.md)

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Topic-Driven Flow | Importance is central to exams. Retrieval should support, not drive, output. |
| Deterministic Marks | Marks are consistent with question types (Definition/Explanation/Discussion). |
| Stable Templates | Reduced hallucination by using template-driven question generation over raw LLM. |
