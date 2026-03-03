# examBrain.py
import re

class ImportanceScorer:
    # Fix 1: The Stop-word Filter
    BLACKLIST = ["introduction", "conclusion", "reference", "bibliography", "index", "preface", "objective"]
    
    # Keyword weights
    KEYWORD_WEIGHTS = {
        "definition": ["define", "meaning", "concept", "is known as"],
        "classification": ["types", "classification", "categories", "kinds"],
        "process": ["steps", "process", "stages", "phases", "cycle"],
        "comparison": ["difference", "contrast", "distinguish", "vs"]
    }

    def score_topic(self, topic, line_metadata):
        # 1. STOP-WORD FILTER
        if any(word in topic.title.lower() for word in self.BLACKLIST):
            return 0.0

        score = 0
        content_lower = topic.content.lower()

        # 2. STRUCTURAL SCORE
        if topic.content_type == 'definition': score += 3
        if any(k in content_lower for k in self.KEYWORD_WEIGHTS["classification"]): 
            score += 2
            topic.detected_type = "classification"
        if any(k in content_lower for k in self.KEYWORD_WEIGHTS["process"]): 
            score += 2
            topic.detected_type = "process"
        
        # Check if node has any children (Chapter uses .sections, Topic uses .subsections)
        children = getattr(topic, 'sections', []) + getattr(topic, 'subsections', [])
        if len(children) > 0: score += 3

        # 3. DENSITY SCORE
        word_count = len(content_lower.split())
        if 100 < word_count < 500: score += 2 # Ideal "Sweet Spot"
        
        # Fix 2: Repetition of Heading keywords in content
        title_words = [w for w in topic.title.lower().split() if len(w) > 3]
        repetition_count = sum(content_lower.count(w) for w in title_words)
        score += min(repetition_count * 0.5, 5) # Cap at 5 points

        # 4. EMPHASIS SCORE
        # Sum bold counts from line metadata
        bold_count = 0
        for i in range(topic.line_start, topic.line_end + 1):
            bold_count += line_metadata.get(i, {}).get("bold_count", 0)
        score += min(bold_count, 5)
        
        if topic.level == 1: score += 2 # Level 1 Headings are often core units

        return round(score, 2)

class QuestionGenerator:
    TEMPLATES = {
        "definition": ["Define {title}.", "What is the concept of {title}?"],
        "classification": ["Explain the different types of {title}.", "Classify {title} with details."],
        "process": ["Describe the steps involved in {title}.", "Explain the process of {title} with a diagram."],
        "default": ["Write a short note on {title}.", "Discuss the importance of {title}."]
    }

    def generate(self, topic):
        # Fix 3: Diagram Trigger
        diagram_keywords = ["figure", "diagram", "flowchart", "illustration"]
        t_type = getattr(topic, 'detected_type', 'default')
        
        template = self.TEMPLATES.get(t_type, self.TEMPLATES['default'])[0]
        
        # Inject diagram requirement if content suggests it
        if any(dk in topic.content.lower() for dk in diagram_keywords):
            template += " (Support with a diagram)"
            
        return template.format(title=topic.title)