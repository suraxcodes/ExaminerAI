---
created: 2026-03-24T17:16:28.847Z
title: Add time-based weighting for past papers
area: tooling
files:
  - src/pastPaperProcessor.py
---

## Problem

All past exam questions are currently treated equally. However, questions from 2023 or 2024 are better predictors of future content than questions from 2015.

## Solution

Enable `PastPaperProcessor` to detect and use years if available in the text.
Implement a time-decay or weighted frequency model:
- 2023 → weight 3
- 2020 → weight 2
- 2015 → weight 1

Integrate this into the `combine_scores` logic for final prioritization.
