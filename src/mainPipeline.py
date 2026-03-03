"""
MAIN DOCUMENT PROCESSING PIPELINE
==================================

This file runs the complete document processing pipeline:
1. Extract text from documents (PDF/DOCX/Images)
2. Build hierarchical structure
3. Score importance of topics
4. Generate predicted exam questions
5. Generate answers using LLM
"""

import json
from pathlib import Path
from documentLoader import DocumentsExtractor
from documentStructure import StructuredDocumentBuilder
from examBrain import ImportanceScorer, QuestionGenerator
from llmResponder import LLMResponder
from tqdm import tqdm
from documentStructure import Topic, Chapter

DOCUMENT_PATH = "../dataSet/Fundamentals_of_Cybersecurity.pdf"
OUTPUT_DIR = "../OutputData"

def main():
    """Main pipeline execution"""
    
    # Create output directory if it doesn't exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("DOCUMENT PROCESSING PIPELINE")
    print("=" * 80)
    print()

    def get_rag_chunks(raw_text, chunk_size=1500, overlap=200):
        """Splits text into fixed-size chunks for RAG"""
        chunks = []
        start = 0
        while start < len(raw_text):
            end = start + chunk_size
            chunk_content = raw_text[start:end] 
        
        # Create a Topic object for each chunk
        chunk_id = (start // (chunk_size - overlap)) + 1
        topic = Topic(
            title=f"Segment {chunk_id}",
            level=2,
            content=chunk_content,
            content_type="default",
            line_start=0, # Not needed for pure RAG
            line_end=0
        )
        chunks.append(topic)
        start += (chunk_size - overlap)
    return chunks

    # STEP 1: Extracting document
    print("STEP 1: Extracting document...")
    print(f"Document: {DOCUMENT_PATH}")
    extraction_result = DocumentsExtractor.extract(DOCUMENT_PATH)
    
    print(f"✓ Extracted {len(extraction_result.raw_text)} characters")
    print(f"✓ File type: {extraction_result.file_type}")
    print(f"✓ Line Metadata Captured: {len(extraction_result.line_metadata) if extraction_result.line_metadata else 0} lines")
    print()

    # STEP 2: Building hierarchical structure
    print("STEP 2: Processing via Pure RAG (Chunking)...")
    all_chunks = get_rag_chunks(extraction_result.raw_text)

    print("STEP 3: Scoring Chunks...")
    scorer = ImportanceScorer()
    for chunk in all_chunks:
        # We pass empty metadata {} because PDFs don't provide bold/italic runs easily
        chunk.importance_score = scorer.score_topic(chunk, {})

    high_value = sorted([t for t in all_chunks if t.importance_score >= 0], 
                    key=lambda x: x.importance_score, reverse=True)

    print(f"✓ Created {len(all_chunks)} chunks. Selected top {len(high_value[:5])} for exam.")

    def score_recursive(node):
        # 1. Score the current node
        node.importance_score = scorer.score_topic(node, extraction_result.line_metadata)
        ranked_topics.append(node)
        
        # 2. Get children safely from either 'sections' (Chapter) or 'subsections' (Topic)
        # Using .get() style logic or getattr
        children = getattr(node, 'sections', []) + getattr(node, 'subsections', [])
        
        for child in children:
            score_recursive(child)

    # 3. Trigger the process for every chapter
    for chapter in structured_doc.chapters:
        score_recursive(chapter)

    # 4. Sort and Filter (Keep scores > 5)
    high_value = sorted([t for t in ranked_topics if t.importance_score > 5], 
                        key=lambda x: x.importance_score, reverse=True)

    print(f"✓ Identified {len(high_value)} high-probability exam topics.")
    
    # 5. STEP 5: Generate the Final Booklet
    print("STEP 5: Generating Final Q&A Booklet...")
    responder = LLMResponder(model_name="deepseek-r1:7b")
    final_booklet = []

    for topic in tqdm(high_value[:5], desc="Generating Answers", unit="question"):
        question = gen.generate(topic)

        assigned_marks = 10 if topic.importance_score > 12 else 5
        
        answer = responder.generate_answer({
            "question": question,
            "context": topic.content,
            "marks": assigned_marks
        })
        
        final_booklet.append({
            "topic": topic.title,
            "importance": topic.importance_score,
            "question": question,
            "answer": answer,
            "marks": assigned_marks
        })

    # Save outputs
    print("STEP 6: Saving results...")
    
    # Save structured doc
    output_dict = builder.to_dict(structured_doc)
    with open(f"{OUTPUT_DIR}/structured_document.json", "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False)
    
    # Save final booklet
    with open(f"{OUTPUT_DIR}/predicted_exam.json", "w", encoding="utf-8") as f:
        json.dump(final_booklet, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to: {OUTPUT_DIR}/")
    print()
    
    print("-" * 80)
    print("PIPELINE COMPLETE ✓")
    print("-" * 80)

if __name__ == "__main__":
    main()
