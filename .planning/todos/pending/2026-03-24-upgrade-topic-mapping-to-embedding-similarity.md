---
created: 2026-03-24T17:16:28.847Z
title: Upgrade topic mapping to embedding similarity
area: tooling
files:
  - src/pastPaperProcessor.py
  - src/smartRetriever.py
---

## Problem

Topic mapping currently uses keyword overlap (string matching) which is brittle and misses semantic matches (e.g. "cybersecurity" vs "information security"). This affects the accuracy of frequency weighting from past papers.

## Solution

Replace string matching in `PastPaperProcessor.map_questions_to_topics` with vector-based embedding similarity using the existing `SmartRetriever`. This will allow catching conceptually similar questions even if keywords differ.
