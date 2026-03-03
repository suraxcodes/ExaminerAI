
class ImportanceScorer:
    def __init__(self):
        self.exam_keywords = {
            "definition": {
                "patterns": ["define", "what is", "meaning", "concept", "refers to", "is defined as"],
                "weight": 3,
                "context": ["fundamental", "basic", "core", "essence"]
            },
            "classification": {
                "patterns": ["types", "classification", "categories", "kinds", "classes", "taxonomy"],
                "weight": 2,
                "context": ["classified as", "divided into", "grouped into", "categories include"]
            },
            "process": {
                "patterns": ["steps", "process", "cycle", "stages", "phases", "procedure", "method"],
                "weight": 2,
                "context": ["first", "second", "finally", "sequence", "flow"]
            },
            "comparison": {
                "patterns": ["difference", "contrast", "distinguish", "versus", "vs", "compared to"],
                "weight": 2,
                "context": ["similarly", "however", "whereas", "unlike", "both"]
            },
            "application": {
                "patterns": ["application", "use case", "example", "implementation", "practical"],
                "weight": 2,
                "context": ["for instance", "such as", "e.g.", "example includes"]
            }
        }
        
        # Visual/formatting indicators
        self.formatting_indicators = {
            "bullet_points": ["•", "●", "-", "•", "*", "·"],
            "numbered_lists": ["1.", "2.", "3.", "firstly", "secondly"],
            "headings": ["#", "##", "###", "heading", "title", "section"],
            "emphasis": ["bold", "strong", "highlight", "important", "note that"]
        }

    def calculate_score(self, topic, line_meta):
        score = 0
        content_lower = topic.content.lower()
        
        # --- STRUCTURAL SCORE ---
        if any(k in content_lower[:100] for k in self.exam_keywords["definition"]):
            score += 3
            topic.detected_type = "definition"
        if any(k in content_lower for k in self.exam_keywords["classification"]):
            score += 2
            topic.detected_type = "classification"
        if any(k in content_lower for k in self.exam_keywords["process"]):
            score += 2
            topic.detected_type = "process"
        if "•" in topic.content or "1." in topic.content:
            score += 2
            
        # --- DENSITY SCORE ---
        word_count = len(topic.content.split())
        if 50 < word_count < 300: score += 2 # Ideal length for a 5-mark answer
        score += len(topic.subsections) * 3  # Multiple subheadings

        # --- EMPHASIS SCORE ---
        # Sum bold counts from the line_metadata for this topic's range
        topic_bold_count = sum(line_meta[i]["bold_count"] 
                               for i in range(topic.line_start, topic.line_end + 1) 
                               if i in line_meta)
        score += min(topic_bold_count, 5) # Cap it so it doesn't skew too much
        
        return score

    class QuestionGenerator:
        TEMPLATES = {
        "definition": ["Define {title}.", "What do you mean by {title}?"],
        "classification": ["Explain different types of {title}.", "Classify {title} in detail."],
        "process": ["Describe the steps involved in {title}.", "Explain the process of {title} with a diagram."],
        "default": ["Write a short note on {title}.", "Explain the importance of {title}."]
    }

        def generate(self, topic):
            # If using RAG chunks, the title is generic. 
            # Let's ask the LLM or use a simple heuristic to find a 'real' title from content.
            first_line = topic.content.split('\n')[0][:50] 
            return f"Based on the following section ('{first_line}...'), write a detailed exam question."