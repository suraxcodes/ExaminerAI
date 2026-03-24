"""
pastPaperProcessor.py
=====================
Extracts questions from past paper text, cleans them, and maps them to
syllabus chunks for frequency analysis.
"""

import re
from typing import List, Dict

class PastPaperProcessor:
    def __init__(self):
        # Patterns for question splitting: Q1, 1., (a), etc.
        self.question_patterns = [
            r"Q\d+[:.]?",    # Q1:, Q2.
            r"\d+\s*[\).]",  # 1), 1.
            r"\([a-z]\)",    # (a), (b)
            r"\[\d+\]",      # [1], [2]
        ]

    def extract_question_marks(self, text: str) -> List[Dict]:
        """Split text into individual questions and extract their mark values."""
        lines = text.split("\n")
        raw_questions = []
        current_q = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
            is_new_q = False
            for pattern in self.question_patterns:
                if re.match(pattern, line):
                    is_new_q = True
                    break
            
            if is_new_q:
                if current_q: raw_questions.append(" ".join(current_q))
                current_q = [line]
            else:
                if current_q: current_q.append(line)
        if current_q: raw_questions.append(" ".join(current_q))
            
        # Extract marks from each question
        results = []
        for rq in raw_questions:
            # Pattern for [10], [5 marks], (2m)
            mark_match = re.search(r"[\(\[](\d+)\s*(?:marks?|m)?[\)\]]", rq, flags=re.IGNORECASE)
            marks = int(mark_match.group(1)) if mark_match else 0
            
            # Clean question text
            clean_q = re.sub(r"^(?:Q\d+[:.]?|\d+\s*[\).\(]?|[a-z]\s*[\).\(]|[\(\[].*?[\)\]])", "", rq).strip()
            clean_q = re.sub(r"\[\d+\s*marks?\]|\(\d+\s*m\)", "", clean_q, flags=re.IGNORECASE).strip()
            
            if clean_q:
                results.append({"text": clean_q, "marks": marks})
        return results

    def get_year_weight(self, text: str) -> float:
        """Detect the most recent year mentioned in the text and return its weight."""
        # Find all 4-digit numbers between 2000 and 2026
        years = re.findall(r"\b(20[0-2][0-9])\b", text)
        if not years:
            return 1.0  # Default weight
            
        recent_year = int(max(years))
        
        # Mapping logic:
        # 2023+ -> weight 3.0
        # 2020-2022 -> weight 2.0
        # <2020 -> weight 1.0
        if recent_year >= 2023:
            return 3.0
        elif recent_year >= 2020:
            return 2.0
        else:
            return 1.0

    def map_questions_to_topics(self, question_data: List[Dict], retriever, year_weight: float = 1.0) -> Dict[str, Dict]:
        """
        Map cleaned questions to topic chunks and learn mark distribution.
        Uses soft assignment: each question can map to multiple topics (top_k=3).
        """
        mapping = {}
        
        for item in question_data:
            q_text = item["text"]
            q_marks = item.get("marks", 0)
            
            if len(q_text.split()) < 3:
                continue
                
            # UPGRADE: Multiple result discovery (Better coverage)
            search_results = retriever.search(q_text, top_k=3)
            if not search_results:
                continue

            # Calculate a dynamic mean-based threshold for this specific question
            all_scores = [r['relevance_score'] for r in search_results]
            mean_sim = sum(all_scores) / len(all_scores) if all_scores else 0
            q_threshold = max(0.35, mean_sim)
            
            # Filter results above threshold
            valid_hits = [r for r in search_results if r['relevance_score'] >= q_threshold]
            if not valid_hits:
                continue

            # Distribute weights proportionally among topics
            total_score = sum(h['relevance_score'] for h in valid_hits)
            
            for hit in valid_hits:
                chunk_title = hit['chunk'].title
                score = hit['relevance_score']
                
                # Assign proportional weight to this topic
                weight = score / total_score if total_score > 0 else 1.0
                full_weight = weight * year_weight

                if chunk_title not in mapping:
                    mapping[chunk_title] = {"freq": 0.0, "marks_dist": {}}
                
                target = mapping[chunk_title]
                target["freq"] += full_weight
                
                # Store mark distribution (weighted)
                if q_marks > 0:
                    dist = target["marks_dist"]
                    dist[q_marks] = dist.get(q_marks, 0.0) + full_weight
                
        return mapping

    @staticmethod
    def normalize_title(title: str) -> str:
        """Standardize titles to prevent redundant mapping."""
        if not title: return ""
        return " ".join(title.lower().split())

    @staticmethod
    def combine_scores(mapping: Dict[str, Dict], topics: List, alpha: float = 5.0, beta: float = 1.0):
        """
        Merges past paper freq into importance scores with tunable weights.
        final = (alpha * freq) + (beta * importance)
        """
        for topic in topics:
            norm_title = PastPaperProcessor.normalize_title(topic.title)
            # Find in mapping using normalized match
            match = None
            for m_title, data in mapping.items():
                if PastPaperProcessor.normalize_title(m_title) == norm_title:
                    match = data
                    break
            
            if match:
                freq = match.get("freq", 0.0)
                topic.frequency = freq
                topic.final_score = (alpha * freq) + (beta * getattr(topic, "importance_score", 0))
                # Store preference levels
                dist = match.get("marks_dist", {})
                levels = []
                if dist.get(2, 0) > 0: levels.append("definition")
                if dist.get(5, 0) > 0: levels.append("explain")
                if dist.get(10, 0) > 0: levels.append("discuss")
    def deduplicate_questions(self, questions: List[Dict], threshold=0.85) -> List[Dict]:
        """Groups similar questions but keeps meaningful variations (marks/framing)."""
        import difflib
        if not questions: return []
        
        unique_qs = []
        for q in questions:
            is_dup = False
            for u in unique_qs:
                sim = difflib.SequenceMatcher(None, q['text'].lower(), u['text'].lower()).ratio()
                if sim >= threshold:
                    # It's highly similar text. Is it a meaningful variation?
                    if q.get('marks') == u.get('marks'):
                        # Same marks, same text -> duplicate
                        is_dup = True
                        break
            if not is_dup:
                unique_qs.append(q)
        return unique_qs

    def extract_question_marks(self, text: str) -> List[Dict]:
        """Extracts questions and marks from past paper text."""
        # Simple regex for "1. Question text ... [5 marks]"
        import re
        patterns = [
            r"(?P<text>.*?)\s*\[(?P<marks>\d+)\s*marks?\]",
            r"(?P<marks>\d+)\.\s*(?P<text>.*)"
        ]
        
        results = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line: continue
            
            for pattern in patterns:
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    q_text = m.group("text").strip()
                    # UPGRADE: Length-based filter (Option 6)
                    if len(q_text.split()) < 4:
                        continue
                        
                    try:
                        q_marks = int(m.group("marks"))
                    except:
                        q_marks = 0
                    results.append({"text": q_text, "marks": q_marks})
                    break
        return results
