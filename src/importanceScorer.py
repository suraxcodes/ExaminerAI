"""
importanceScorer.py
====================
Standalone importance scorer for document topics.
Scores topics based on structural signals, keyword density,
content length, and bold emphasis from line metadata.

Also provides a top-level QuestionGenerator for template-based
question generation (used as fallback when LLM is unavailable).
"""

import re
import random


class ImportanceScorer:
    """
    Scores a Topic's exam relevance using multiple signals:
    - Structural keywords (definitions, classifications, processes, comparisons, applications)
    - Bullet/list presence
    - Content density (word count sweet spot)
    - Subsection depth
    - Bold emphasis from DOCX line metadata
    """

    # Topics whose titles match these are likely boilerplate – score them 0
    BLACKLIST = [
        "introduction", "conclusion", "reference", "bibliography",
        "index", "preface", "objective", "table of contents"
    ]

    def __init__(self):
        self.exam_keywords = {
            "definition": {
                "patterns": ["define", "what is", "meaning", "concept", "refers to", "is defined as"],
                "weight": 3,
            },
            "classification": {
                "patterns": ["types", "classification", "categories", "kinds", "classes", "taxonomy"],
                "weight": 2,
            },
            "process": {
                "patterns": ["steps", "process", "cycle", "stages", "phases", "procedure", "method"],
                "weight": 2,
            },
            "comparison": {
                "patterns": ["difference", "contrast", "distinguish", "versus", "vs", "compared to"],
                "weight": 2,
            },
            "application": {
                "patterns": ["application", "use case", "example", "implementation", "practical"],
                "weight": 2,
            },
        }

        # Visual/formatting signals (used for bullet detection)
        self.formatting_indicators = {
            "bullet_points": ["•", "●", "-", "*", "·"],
            "numbered_lists": ["1.", "2.", "3.", "firstly", "secondly"],
        }

    def calculate_score(self, topic, line_meta: dict) -> float:
        """
        Compute importance score for a single topic.

        Args:
            topic:     A Topic (or Chapter) dataclass object.
            line_meta: Dict mapping line_index -> {"bold_count": int, ...}
                       Pass an empty dict {} if metadata is unavailable.

        Returns:
            Numeric score (float). Higher = more important.
        """
        # --- BLACKLIST FILTER ---
        if hasattr(topic, "title") and any(
            w in topic.title.lower() for w in self.BLACKLIST
        ):
            return 0.0

        score = 0.0
        content_lower = topic.content.lower()

        # --- STRUCTURAL SCORE ---
        # Check first 300 chars for definition signals (they usually appear early)
        if any(k in content_lower[:300] for k in self.exam_keywords["definition"]["patterns"]):
            score += 3   # weight for definitions
            topic.detected_type = "definition"

        if any(k in content_lower for k in self.exam_keywords["classification"]["patterns"]):
            score += 2   # weight for classifications
            if not hasattr(topic, "detected_type") or topic.detected_type == "default":
                topic.detected_type = "classification"

        if any(k in content_lower for k in self.exam_keywords["process"]["patterns"]):
            score += 2   # weight for processes
            if not hasattr(topic, "detected_type") or topic.detected_type == "default":
                topic.detected_type = "process"

        if any(k in content_lower for k in self.exam_keywords["comparison"]["patterns"]):
            score += 2   # weight for comparisons

        if any(k in content_lower for k in self.exam_keywords["application"]["patterns"]):
            score += 2   # weight for applications

        # Bullet / numbered list presence → structured content
        if "•" in topic.content or re.search(r"\b1\.", topic.content):
            score += 2

        # --- DENSITY SCORE ---
        word_count = len(topic.content.split())
        if 50 < word_count < 500:
            score += 2   # Sweet spot for a 5–10 mark answer

        # --- DEPTH SCORE ---
        # Works for both Chapter (.sections) and Topic (.subsections)
        children = getattr(topic, "sections", []) + getattr(topic, "subsections", [])
        score += len(children) * 1.5   # Each child section adds 1.5 points

        # --- HEADING LEVEL BONUS ---
        # Level-1 headings (chapters) are usually core units
        if getattr(topic, "level", 2) == 1:
            score += 2

        # --- TITLE REPETITION IN CONTENT ---
        # If title words appear frequently in content it's a focused topic
        title_words = [w for w in topic.title.lower().split() if len(w) > 3]
        if title_words:
            repetition = sum(content_lower.count(w) for w in title_words)
            score += min(repetition * 0.5, 5)   # Cap at 5

        # --- EMPHASIS SCORE (DOCX only) ---
        if line_meta:
            # 2. Bold / Formatting signals
            title = topic.title.lower() if topic.title else ""
            bold_count = sum(
                line_meta[i].get("bold_count", 0)
                for i in range(topic.line_start, topic.line_end + 1)
                if i in line_meta
            )

            # UPGRADE: Density matters more than raw count
            total_lines = (topic.line_end - topic.line_start + 1) if topic.line_end > 0 else 1
            bold_density = bold_count / total_lines

            score += min(bold_count, 5) # Raw boost
            score += bold_density * 3   # Density boost

            # UPGRADE: Keyword emphasis (Option 7)
            important_words = ["important", "note", "definition", "key", "essential"]
            content_lower = topic.content.lower()
            for word in important_words:
                if word in content_lower:
                    score += 1

        return round(score, 2)

    def score_topic(self, topic, line_metadata: dict) -> float:
        """Public interface used by mainPipeline.py and examBrain.py."""
        return self.calculate_score(topic, line_metadata)


# ──────────────────────────────────────────────────────
# Top-level QuestionGenerator (fallback when LLM is off)
# ──────────────────────────────────────────────────────
class QuestionGenerator:
    """
    Template-based question generator.
    Used as a fallback when the LLM is unavailable or returns an error.
    """

    TEMPLATES = {
        "definition": [
            "Define {title}.",
            "What do you mean by {title}?",
            "Explain the concept of {title} in detail.",
        ],
        "explain": [
            "Explain the different types/categories of {title}.",
            "Describe the steps or process involved in {title}.",
            "How does {title} work in the context of this subject?",
        ],
        "discuss": [
            "Discuss the importance and practical applications of {title}.",
            "Critically analyze the role of {title} in its domain.",
            "Write a detailed note on {title} with suitable examples.",
        ],
        "compare": [
            "Differentiate between the key aspects of {topic1} and {topic2}.",
            "Compare and contrast {topic1} with {topic2} in the context of this subject.",
            "Explain the relationship between {topic1} and {topic2}.",
        ],
        "default": [
            "Write a short note on {title}.",
            "Explain {title} with examples.",
        ],
    }
    # Keep aliases for backward compatibility or detected types
    TEMPLATES["classification"] = TEMPLATES["explain"]
    TEMPLATES["process"] = TEMPLATES["explain"]
    TEMPLATES["application"] = TEMPLATES["discuss"]
    TEMPLATES["comparison"] = TEMPLATES["compare"]

    # Keywords in content that suggest a diagram is needed
    DIAGRAM_KEYWORDS = ["figure", "diagram", "flowchart", "illustration", "architecture"]

    def generate(self, topic, level: str = "default", related_topic=None) -> str:
        """
        Generate a question for the given topic using the best matching template.
        Supports level 'compare' if related_topic is provided.
        """
        if level == "default":
            t_type = getattr(topic, "detected_type", "default")
        else:
            t_type = level

        if t_type not in self.TEMPLATES:
            t_type = "default"

        templates = self.TEMPLATES[t_type]
        template = random.choice(templates)

        if t_type == "compare" and related_topic:
            question = template.format(topic1=topic.title, topic2=related_topic.title)
        else:
            # Use a meaningful title; fall back to first content line
            title = topic.title.strip()
            if not title or title.lower().startswith(("segment", "paragraph")):
                title = topic.content.split("\n")[0][:60].strip()
            question = template.format(title=title)

        # Inject diagram requirement if content suggests it
        if any(dk in topic.content.lower() for dk in self.DIAGRAM_KEYWORDS):
            question += " (Support your answer with a neat diagram.)"

        return question