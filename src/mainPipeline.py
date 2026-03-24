"""
MAIN DOCUMENT PROCESSING PIPELINE
==================================

This file runs the complete document processing pipeline:
1. Extract text from documents (PDF/DOCX/Images)
2. Clean the extracted text (remove noise, headers, page numbers)
3. Build hierarchical document structure (chapters, sections)
4. Score and filter topics by importance
5. Create a semantic index from structure-based chunks
6. Search for multiple syllabus topics
7. Generate predicted exam questions and answers via LLM
"""

import logging
import json
import sys
import os
from pathlib import Path
from typing import List
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from documentLoader import DocumentsExtractor
from documentsCLearing import DocumentCleaner
from documentStructure import StructuredDocumentBuilder, Topic
from importanceScorer import ImportanceScorer, QuestionGenerator
from llmResponder import LLMResponder
from smartRetriever import SmartRetriever
from tqdm import tqdm

import argparse

# Default Configuration
DEFAULT_INC_PATH = "../dataSet/Fundamentals_of_Cybersecurity.pdf"
DEFAULT_OUT_DIR  = "../OutputData"
DEFAULT_THRESHOLD = 3
DEFAULT_MODEL = "deepseek-r1:7b"

# ──────────────────────────────────────────────
# LOGGING SETUP  (improvement #11)
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# HELPER: topic extraction (improvement #9)
# ──────────────────────────────────────────────
def extract_topics(structured_doc, scorer, line_metadata, threshold=3, max_topics=15) -> List[str]:
    """
    Automatically extract relevant syllabus topics from the structured document.
    Uses the importance scorer to filter for significant sections.
    """
    topics = []
    
    for chapter in structured_doc.chapters:
        # Check chapter itself
        if chapter.title and scorer.score_topic(chapter, line_metadata) >= threshold:
            topics.append(chapter.title)
            
        # Check sections
        for section in chapter.sections:
            _extract_from_list(section, scorer, line_metadata, threshold, topics)
            
    # De-duplicate while preserving order
    topics = list(dict.fromkeys(topics))
    # Fallback: if no headings detected, use generic chunks if available
    if not topics and structured_doc.chapters:
        log.warning("No high-importance topics extracted - check selection criteria.")
        
    return topics[:max_topics]

def _extract_from_list(topic: Topic, scorer, line_meta, threshold, out: List[str]):
    if topic.title and scorer.score_topic(topic, line_meta) >= threshold:
        out.append(topic.title)
    for sub in topic.subsections:
        _extract_from_list(sub, scorer, line_meta, threshold, out)

# ──────────────────────────────────────────────
# HELPER: flatten a StructuredDocument into Topics
# ──────────────────────────────────────────────
def flatten_structure(structured_doc) -> List[Topic]:
    """
    Convert the nested chapter/section hierarchy into a flat list of Topics.
    Each Topic already carries .content, .title, .level, etc.
    This replaces the naive character-slice get_rag_chunks() approach.
    """
    chunks: List[Topic] = []

    for chapter in structured_doc.chapters:
        # Treat the chapter itself as a top-level chunk if it has content
        if chapter.content.strip():
            chapter_topic = Topic(
                title=chapter.title,
                level=chapter.level,
                content=chapter.content,
                content_type=chapter.content_type,
                line_start=chapter.line_start,
                line_end=chapter.line_end,
            )
            chunks.append(chapter_topic)

        # Recurse into every section and subsection
        for section in chapter.sections:
            _collect_topics(section, chunks)

    return chunks


def _collect_topics(topic: Topic, out: List[Topic]):
    """Recursively collect a Topic and all its subsections."""
    if topic.content.strip():
        out.append(topic)
    for sub in topic.subsections:
        _collect_topics(sub, out)


import statistics

# ──────────────────────────────────────────────
# HELPER: Compute Topic Similarity (STRICTLY MEASUREMENT)
# ──────────────────────────────────────────────
def compute_topic_similarity(topic1, topic2, retriever) -> float:
    """Uses retriever purely as a measurement tool to find similarity score."""
    query = topic1.title
    results = retriever.search(query, top_k=10)
    for r in results:
        if r['chunk'].title == topic2.title:
            return float(r['relevance_score'])
    return 0.0

def cluster_topics(topics: List, retriever, threshold=0.75) -> List:
    """
    Groups highly similar topics into a single representative entry.
    Merges content and combines scores.
    """
    if not topics: return []
    
    unique_topics = []
    merged_indices = set()
    
    for i, t1 in enumerate(topics):
        if i in merged_indices: continue
        
        current_cluster = [t1]
        for j, t2 in enumerate(topics[i+1:], i+1):
            if j in merged_indices: continue
            
            # Use retriever to measure similarity between titles
            sim = compute_topic_similarity(t1, t2, retriever)
            if sim >= threshold:
                current_cluster.append(t2)
                merged_indices.add(j)
        
        # Merge the cluster into a single Topic
        if len(current_cluster) > 1:
            prime = current_cluster[0]
            # Combine content slightly (summary approach)
            prime.content = "\n\n".join(set(c.content for c in current_cluster))
            # Sum frequency and average importance
            prime.final_score = sum(getattr(c, "final_score", 0) for c in current_cluster)
            prime.importance_score = statistics.mean([getattr(c, "importance_score", 0) for c in current_cluster])
            prime.frequency = sum(getattr(c, "frequency", 0) for c in current_cluster)
            unique_topics.append(prime)
        else:
            unique_topics.append(t1)
            
    return unique_topics

def evaluate(predicted_topics: List[str], actual_topics: List[str]) -> dict:
    """
    Calculates metrics for prediction accuracy against actual exam topics.
    """
    if not actual_topics:
        return {"recall": 0.0, "top_5_acc": 0.0, "hits": []}

    # Normalize for comparison
    from pastPaperProcessor import PastPaperProcessor
    norm_actual = [PastPaperProcessor.normalize_title(t) for t in actual_topics]
    norm_pred   = [PastPaperProcessor.normalize_title(t) for t in predicted_topics]
    
    hits = [t for t in predicted_topics if PastPaperProcessor.normalize_title(t) in norm_actual]
    recall = len(hits) / len(actual_topics) if actual_topics else 0
    
    # Top-5 Accuracy
    top_5_pred = norm_pred[:5]
    top_5_hits = [t for t in norm_actual if t in top_5_pred]
    top_5_acc = len(top_5_hits) / min(len(norm_actual), 5) if norm_actual else 0

    precision = len(hits) / len(predicted_topics) if predicted_topics else 0
    
    # Composite Score (50% Recall, 30% Precision, 20% Top-5)
    composite_score = (0.5 * recall) + (0.3 * precision) + (0.2 * top_5_acc)

    return {
        "recall": round(recall, 2),
        "precision": round(precision, 2),
        "top_5_acc": round(top_5_acc, 2),
        "composite_score": round(composite_score, 2),
        "hits": hits
    }

def generate_template_answer(topic) -> str:
    """Deterministic fallback when LLM fails or lacks info."""
    content_snippet = topic.content[:400].strip()
    return (
        f"{topic.title} is a significant concept in this curriculum. "
        f"Key details from the source material include:\n\n"
        f"{content_snippet}..."
    )

# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────
def run_calibration_loop(all_chunks, actual_topics, retriever):
    """
    Search for best alpha/beta weights using a grid search over composite score.
    """
    best_score = -1
    best_params = (5.0, 1.0)
    baseline_recall = 0.4  # Hardcoded baseline for drift detection
    
    print("\n[CALIBRATION] Running grid search for optimal weights...")
    for alpha in [2.0, 5.0, 10.0]:
        for beta in [0.5, 1.0, 3.0]:
            # Reset scores
            for c in all_chunks: 
                c.final_score = (alpha * getattr(c, "frequency", 0)) + (beta * getattr(c, "importance_score", 0))
            
            sorted_v = sorted(all_chunks, key=lambda x: x.final_score, reverse=True)
            top_v = [c.title for c in sorted_v[:15]]
            res = evaluate(top_v, actual_topics)
            
            print(f"  > Alpha={alpha}, Beta={beta} | Score: {res['composite_score']} (Recall: {res['recall']}, Prec: {res['precision']})")
            if res['composite_score'] > best_score:
                best_score = res['composite_score']
                best_params = (alpha, beta)
                
    # Drift Detection (Todo 6)
    if best_score >= 0 and res['recall'] < baseline_recall:
        print(f"  ⚠ ALERT: Model drift detected! Current recall ({res['recall']}) < baseline ({baseline_recall}).")

    print(f"[CALIBRATION] Best Params: Alpha={best_params[0]}, Beta={best_params[1]} (Score: {best_score})\n")
    return best_params
def ensure_ollama_running():
    import urllib.request
    from urllib.error import URLError
    import subprocess
    import time
    import os
    
    url = "http://localhost:11434"
    try:
        urllib.request.urlopen(url, timeout=2)
    except URLError:
        print("\n[INFO] Ollama is not running. Starting 'ollama serve' in background...")
        try:
            if os.name == 'nt':
                creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                subprocess.Popen(["ollama", "serve"], creationflags=creation_flags)
            else:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            for _ in range(20):
                time.sleep(1)
                try:
                    urllib.request.urlopen(url, timeout=1)
                    print("[INFO] Ollama started successfully.\n")
                    return
                except URLError:
                    pass
            print("\n  ⚠ WARNING: Ollama took too long to start. Predictions may fail.")
        except Exception as e:
            print(f"\n  ⚠ WARNING: Failed to start Ollama automatically: {e}")

def main():
    """Main pipeline execution"""
    ensure_ollama_running()
    
    parser = argparse.ArgumentParser(description="EXAMER AI – Document Processing Pipeline")
    parser.add_argument("--input", default=DEFAULT_INC_PATH, help="Path to textbook file (PDF/DOCX/Image)")
    parser.add_argument("--output", default=DEFAULT_OUT_DIR, help="Directory to save the generated booklet")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Importance threshold (1-10)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Local LLM model name (Ollama)")
    parser.add_argument("--study-time", default="unlimited", help="Available study time (e.g., 2h, 1d, unlimited)")
    parser.add_argument("--calibrate", action="store_true", help="Run alpha/beta calibration loop")
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXAMER AI – DOCUMENT PROCESSING PIPELINE")
    print("=" * 80)
    print()

    # ── STEP 1: Extract document ──────────────────────────────────────────
    print("STEP 1: Extracting document...")
    log.info("Starting document extraction from: %s", args.input)
    extraction_result = DocumentsExtractor.extract(args.input)
    print(f"  ✓ Extracted {len(extraction_result.raw_text):,} characters")
    print(f"  ✓ File type : {extraction_result.file_type}")
    print()

    # ── STEP 2: Clean the extracted text ─────────────────────────────────
    print("STEP 2: Cleaning document text...")
    log.info("Running DocumentCleaner...")
    cleaner = DocumentCleaner()
    cleaning_result = cleaner.clean(extraction_result.raw_text)
    clean_text = cleaning_result.cleaned_text
    print(f"  ✓ Clean text : {len(clean_text):,} characters")
    print(f"  ✓ Removed   : {cleaning_result.statistics['characters_removed']:,} characters of noise")

    # Patch the extraction_result so StructuredDocumentBuilder sees clean text
    extraction_result.raw_text = clean_text
    print()

    # ── STEP 3: Build hierarchical structure ─────────────────────────────
    print("STEP 3: Building document hierarchy (chapters & sections)...")
    log.info("Running StructuredDocumentBuilder...")
    builder = StructuredDocumentBuilder()
    structured_doc = builder.build(extraction_result)
    print(f"  ✓ Detected {len(structured_doc.chapters)} chapters")
    print()

    # ── STEP 4: Flatten structure → Topics (structure-based chunking) ─────
    print("STEP 4: Converting structure to semantic chunks...")
    all_chunks = flatten_structure(structured_doc)
    
    # Fallback: if document had no detectable headings, chunk by paragraphs
    if not all_chunks:
        log.warning("No structured chunks found – falling back to paragraph chunking.")
        print("  ⚠ No headings detected. Falling back to paragraph-based chunking.")
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if len(p.strip()) > 100]
        for idx, para in enumerate(paragraphs):
            all_chunks.append(Topic(
                title=f"Paragraph {idx + 1}",
                level=2,
                content=para,
                content_type="paragraph",
                line_start=0,
                line_end=0,
            ))
    print(f"  ✓ Total semantic chunks: {len(all_chunks)}")
    print()

    # ── STEP 5: Score and filter by importance ────────────────────────────
    print("STEP 5: Scoring and filtering important topics...")
    log.info("Running ImportanceScorer with threshold=%d", args.threshold)
    scorer = ImportanceScorer()
    line_metadata = extraction_result.line_metadata or {}

    total_content_len = 0
    for chunk in all_chunks:
        score = scorer.score_topic(chunk, line_metadata)
        chunk.importance_score = score
        chunk.final_score = score
        chunk.frequency = 0.0
        total_content_len += len(chunk.content)

    # ── STEP 5.1: Quality Checks ─────────────────────────────────────────
    avg_chunk_len = total_content_len / len(all_chunks) if all_chunks else 0
    if len(all_chunks) < 5:
        log.error("ABORT: Document too small for reliable prediction (found %d chunks).", len(all_chunks))
        print("  ✖ FAILURE: Source document is too small for reliable exam prediction.")
        return
    if avg_chunk_len < 200:
        log.warning("QUALITY WARNING: Low content density detected (avg chunk len: %.1f).", avg_chunk_len)
        print("  ⚠ WARNING: Low content density. Predictions may be unreliable.")

    # ── STEP 5.5: Build semantic index ────────────────────────────────────
    print("STEP 5.5: Building semantic index for processing...")
    log.info("Initialising SmartRetriever...")
    retriever = SmartRetriever()
    retriever.prepare_index(all_chunks)
    print()

    # ── STEP 6: Optional Past Paper Frequency Analysis ────────────────────
    mapped_past_qs = 0
    total_past_qs = 0
    mapping = {}
    
    past_paper_path = Path(args.input).parent / "past_paper.txt"
    if past_paper_path.exists():
        from pastPaperProcessor import PastPaperProcessor
        print(f"  ✓ Found past paper at: {past_paper_path}")
        processor = PastPaperProcessor()
        with open(past_paper_path, "r", encoding="utf-8") as f:
            pp_text = f.read()
            
        year_weight = processor.get_year_weight(pp_text)
        print(f"  ✓ Detected past paper relevance weight: {year_weight}x")

        # Deduplicate past questions before mapping (Todo 7)
        question_data = processor.extract_question_marks(pp_text)
        print(f"  ✓ Extracted {len(question_data)} raw questions")
        
        # Deduplication based on similarity
        unique_qs = processor.deduplicate_questions(question_data)
        print(f"  ✓ Deduplicated: {len(unique_qs)} high-signal questions remaining.")
        
        total_past_qs = len(unique_qs)
        mapping = processor.map_questions_to_topics(unique_qs, retriever, year_weight=year_weight)
        mapped_past_qs = len(mapping)
        
        # Calibration (Todo 2)
        alpha, beta = 5.0, 1.0
        if args.calibrate:
            actual_titles = list(mapping.keys())
            # Pre-apply importance scores for calibration loop
            alpha, beta = run_calibration_loop(all_chunks, actual_titles, retriever)
            
        PastPaperProcessor.combine_scores(mapping, all_chunks, alpha=alpha, beta=beta)
        
        # Contradiction Handling: Deduct if importance is too low despite high freq
        for chunk in all_chunks:
            if getattr(chunk, "importance_score", 0) < 2.0 and getattr(chunk, "frequency", 0) > 0.5:
                # This might be a false positive from a noisy past paper mapping
                chunk.final_score *= 0.5 
                
        print(f"  ✓ Combined {len(mapping)} past questions into weighted scores.")
        log.info("Pipeline Health: mapping coverage %d/%d (%.1f%%)", mapped_past_qs, total_past_qs, (mapped_past_qs/total_past_qs*100) if total_past_qs > 0 else 0)

    # Cluster overlapping topics (Todo 4)
    print("STEP 6.2: Clustering overlapping topics...")
    clustered_chunks = cluster_topics(all_chunks, retriever, threshold=0.75)
    print(f"  ✓ Merged overlapping topics: {len(all_chunks)} → {len(clustered_chunks)}")

    # Sort chunks by final_score
    sorted_chunks = sorted(clustered_chunks, key=lambda x: getattr(x, "final_score", 0), reverse=True)
    
    # Pruning logic
    if sorted_chunks:
        scores = [float(getattr(c, "final_score", 0)) for c in sorted_chunks]
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        pruning_threshold = mean_score + (0.3 * std_dev)
        top_chunks = [c for c in sorted_chunks if float(getattr(c, "final_score", 0)) >= pruning_threshold]
        
        # Study-Time Aware Filtering (Todo 6)
        if args.study_time.lower().endswith("h") and args.study_time.lower()[:-1].isdigit():
            limit = int(args.study_time.lower().replace("h", "")) * 2 # 2 topics per hour
            top_chunks = top_chunks[:limit]
            print(f"  ✓ Study Mode ({args.study_time}): Focused on top {limit} topics.")
        elif args.study_time.lower().endswith("d") and args.study_time.lower()[:-1].isdigit():
            limit = int(args.study_time.lower().replace("d", "")) * 8 # 8 topics per day
            top_chunks = top_chunks[:limit]
            print(f"  ✓ Study Mode ({args.study_time}): Focused on top {limit} topics.")
        else:
            top_chunks = top_chunks[:15] # Default
            
        top_score = scores[0] if scores else 1.0
    else:
        top_chunks = []
        top_score = 1.0

    # ── STEP 6.5: Failure Detection ──────────────────────────────────────
    if len(top_chunks) < 3:
        log.warning("FAILURE DETECTION: Insufficient strong topics found.")
        print("  ⚠ Low confidence: No high-priority syllabus topics identified.")

    print(f"  ✓ Valid topics selected : {len(top_chunks)}")
    print()

    # ── STEP 7: Generate Booklet ─────────────────────────────────────────
    print("STEP 7: Generating booklet (Topic-Driven Flow)...")
    responder     = LLMResponder(model_name=args.model)
    question_gen  = QuestionGenerator()
    final_booklet = []
    seen_questions = set()

    for idx, chunk in enumerate(tqdm(top_chunks, desc="  Q&A generator", unit="topic")):
        topic_title = chunk.title or f"Section: {chunk.content[:40]}..."
        chunk_score = float(getattr(chunk, "final_score", 0))
        freq_count  = getattr(chunk, "frequency", 0)
        
        score_ratio = chunk_score / top_score if top_score > 0 else 0
        if score_ratio >= 0.8: confidence = "High"
        elif score_ratio >= 0.5: confidence = "Medium"
        else: confidence = "Low"

        # PRIORITY TAGGING (Todo 5)
        if idx < 3 and score_ratio > 0.8: priority = "Priority 1: Must Study"
        elif idx < 8: priority = "Priority 2: Should Study"
        else: priority = "Priority 3: Optional / Extended"

        levels = getattr(chunk, "preferred_levels", ["definition", "explain", "discuss"])
        
        related_topic = None
        if idx < len(top_chunks) - 1:
            next_topic = top_chunks[idx + 1]
            similarity_score = compute_topic_similarity(chunk, next_topic, retriever)
            if (similarity_score > 0.6 and 
                chunk_score > pruning_threshold and 
                getattr(next_topic, "final_score", 0) > pruning_threshold):
                related_topic = next_topic
                if "compare" not in levels: levels.append("compare")

        for level in levels:
            if level == "compare" and not related_topic: continue

            question = question_gen.generate(chunk, level=level, related_topic=related_topic)
            if question in seen_questions: continue
            seen_questions.add(question)

            # Marks
            if level == "definition": marks = 2
            elif level == "explain": marks = 5
            elif level == "compare": marks = 7
            else: marks = 10

            # Retrieval
            context_query = f"{topic_title} {getattr(related_topic, 'title', '')} {level}"
            search_results = retriever.search(context_query, top_k=2)
            combined_context = "\n\n".join([r['chunk'].content for r in search_results])
            if chunk.content not in combined_context: combined_context = chunk.content + "\n\n" + combined_context
            if related_topic and hasattr(related_topic, 'content') and related_topic.content not in combined_context:
                combined_context += "\n\n" + related_topic.content

            # Generate Answer
            answer = responder.generate_answer({"question": question, "context" : combined_context, "marks": marks})
            if any(refusal in answer.lower() for refusal in ["error", "not contain enough information", "cannot answer"]):
                answer = generate_template_answer(chunk)

            # Explainability
            reason_parts = []
            if getattr(chunk, "importance_score", 0) > 5.0: reason_parts.append("Strong structural signals")
            if freq_count > 2.0: reason_parts.append("Frequently asked in past papers")
            if score_ratio > 0.9: reason_parts.append("Top syllabus priority")
            reason = " + ".join(reason_parts) if reason_parts else "Meets relevance threshold"

            final_booklet.append({
                "topic"          : topic_title,
                "priority"       : priority,
                "level"          : level,
                "final_score"    : round(chunk_score, 2),
                "confidence"     : confidence,
                "reason"         : reason,
                "question"       : question,
                "answer"         : answer,
                "marks"          : marks,
                "explainability" : {
                    "importance_score": round(getattr(chunk, "importance_score", 0), 2),
                    "past_freq"       : round(freq_count, 1),
                    "score_ratio"     : round(score_ratio, 2)
                }
            })

    # ── STEP 8: Save results ──────────────────────────────────────────────
    print("\nSTEP 8: Saving results...")
    output_path = Path(args.output) / "predicted_exam_v3.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_booklet, f, indent=2, ensure_ascii=False)

    # ── STEP 9: Evaluation ────────────────────────────────────────────────
    if total_past_qs > 0:
        print("\nSTEP 9: Evaluating prediction accuracy...")
        pred_titles = [item["topic"] for item in final_booklet]
        actual_titles = list(mapping.keys())
        results = evaluate(pred_titles, actual_titles)
        
        print(f"  ✓ Topic Recall      : {results['recall']:.2f}")
        print(f"  ✓ Top-5 Accuracy    : {results['top_5_acc']:.2f}")
        print(f"  ✓ Correct Matches   : {len(results['hits'])}")
        log.info("Evaluation results: Recall=%.2f, Top5Acc=%.2f", results['recall'], results['top_5_acc'])

    log.info("Pipeline Complete. Saved %d entries.", len(final_booklet))
    print(f"  ✓ {len(final_booklet)} Q&A entries saved to: {output_path}")
    print()
    print("-" * 80)
    print("PIPELINE COMPLETE ✓")
    print("-" * 80)


if __name__ == "__main__":
    main()
