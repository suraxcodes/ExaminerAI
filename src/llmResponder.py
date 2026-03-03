import openai  # Added missing import
from tqdm import tqdm

class LLMResponder:
    """Handles formatted answer generation using restricted RAG context via Ollama"""
    
    def __init__(self, model_name: str = "deepseek-r1:7b"):
        # Ensure Ollama is running before calling this!
        self.client = openai.OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama" 
        )
        self.model_name = model_name

    def generate_answer(self, question_data: dict):
        """Generates a high-quality answer using the local LLM"""
        question = question_data.get('question', '')
        context = question_data.get('context', '')
        marks = question_data.get('marks', 5)

        # 1. Dynamic logic for depth (This fixes the 'depth_instruction' error)
        if marks <= 2:
            depth_instruction = "Provide a single, precise paragraph of 2-3 sentences."
        elif marks <= 5:
            depth_instruction = f"Provide exactly {marks} distinct bullet points, each with a brief explanation."
        else:
            depth_instruction = "Provide an introductory paragraph, followed by detailed sub-sections for each key point, and a concluding summary."

        # 2. Build the strict prompt
        prompt = f"""
You are an Expert Academic Examiner with 15+ years of experience in curriculum design.

TASK:
Generate a comprehensive, high-quality answer for the provided QUESTION using ONLY the provided CONTEXT.

QUESTION: {question}
ASSIGNED MARKS: {marks}

CONTEXT (SOURCE MATERIAL):
{context}

================================================================================
STRICT EXAMINATION RULES:
================================================================================
1. **CONTENT AUTHORITY:** Use ONLY information explicitly stated in the provided context.
2. **MARK DEPTH:** {depth_instruction}
3. **KEY TERM EMPHASIS:** Bold ALL critical concepts: **key term**.
4. **STRUCTURE:** Use formal academic register.

If the answer cannot be fully constructed from context, state: "The provided context does not contain enough information."
"""

        try:
            # tqdm.write ensures the message doesn't break the progress bar in mainPipeline.py
            tqdm.write(f" [LLM] Processing: {question[:50]}...")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3 # Low temperature for factual consistency
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}"