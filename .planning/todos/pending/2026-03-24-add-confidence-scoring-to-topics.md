---
created: 2026-03-24T17:16:28.847Z
title: Add confidence scoring to topics
area: ui
files:
  - src/mainPipeline.py
---

## Problem

Users currently see final topic scores but have no measure of the system's "confidence" in those scores. This makes it harder to trust the generated questions and priorities.

## Solution

Implement a fast-win confidence metric by normalizing `final_score` (e.g. 0-1 range).
Map normalized scores to categorical outputs:
- **High** (e.g. score > 0.8)
- **Medium** (e.g. 0.5 < score <= 0.8)
- **Low** (e.g. score <= 0.5)

Surface these labels in the final booklet and logs.
