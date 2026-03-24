---
created: 2026-03-24T17:16:28.847Z
title: Implement multi-question generation per topic
area: api
files:
  - src/mainPipeline.py
  - src/importanceScorer.py
---

## Problem

Generating only one question (e.g. definition) per topic is not enough to make the booklet "exam-ready". Real exams explore the same topic from multiple angles (Define → Explain → Discuss).

## Solution

Modify the pipeline to generate 2-3 questions per top topic instead of just one.
Questions should follow a complexity progression:
1.  **Define**: Basic concept identification (2 marks).
2.  **Explain**: Process/Step description (5 marks).
3.  **Discuss/Analyze**: Application/Critique (10 marks).

Update `QuestionGenerator` to support these distinct levels in its template logic.
