# ExamerAI 🎓🤖

**ExamerAI** is an intelligent, fully automated AI pipeline that processes textbooks or lecture notes and turns them into a high-yield, exam-ready predicted Q&A booklet. 

If you've ever stared at a 500-page textbook or messy lecture notes and wondered *"What am I actually going to be tested on?"*, ExamerAI answers that question. It structurally reads your notes, mathematically analyzes past exam questions, maps out exactly what is important, and generates deterministic exam questions—saving you hundreds of hours of manual studying.

---

## 🔎 Deep-Dive: How the Pipeline Works (Step-by-Step)

The core architecture operates over **13 distinct phases**. To ensure absolute reliability and prevent AI hallucination, ExamerAI separates text extraction, mathematical scoring, semantic search, and Local LLM answer generation into distinct, highly controlled steps.

Here is a deep dive into precisely what happens under the hood.

### 1️⃣ Input Stage: Upload Notes & Files
* **What happens:** The user provides a path to their syllabus notes (via `--input`) and any available historical past papers. They can also configure the exact amount of time they have to study (`--study-time 2h` or `1d`). 
* **The Goal:** Provide the foundation. The notes dictate the *universe of knowledge*, and the past historical questions dictate the *pattern of the examiner*.

### 2️⃣ Text Extraction & Cleaning (`documentLoader.py`)
* **What happens:** The system parses the raw input file using specialized libraries—`pdfplumber` for text PDFs, `docx2txt` for Word documents, and `pytesseract` OCR for images or scanned, non-searchable PDFs.
* **The Math/Logic:** It sweeps through page by page, stripping out massive swathes of whitespace, page numbers, and irrelevant floating headers to output a single, contiguous string of clean text. 

### 3️⃣ Structured Document Builder (`documentStructure.py`)
* **What happens:** Sending an unstructured 500-page wall of text to an AI is guaranteed to fail. Instead, ExamerAI detects structural headings (e.g., Markdown `# Heading 1` tags, or inferring headers via capitalization and string length).
* **The Logic:** It splits the giant document into discrete, manageable `Topic` chunks hierarchically (`Chapters → Sections → Topics → Content`). Now, the pipeline has a clean list of isolated topics representing the curriculum. 

### 4️⃣ Importance Scoring (`importanceScorer.py`)
* **What happens:** Not every topic is equal. The pipeline analyzes the `Content` block of every isolated topic strictly using lexical and structural cues.
* **The Logic:** It adds points to the `importance_score` if the topic contains:
  * Bulleted lists (`-`, `*`) 
  * High densities of bolded text 
  * "Action" keywords commonly tested (e.g., *"define"*, *"process"*, *"advantage"*, *"types of"*).
* **Output:** A base *Importance Score* representing the pure academic weight of the note itself.

### 5️⃣ Past Paper Analysis (`pastPaperProcessor.py`)
* **What happens:** If past papers are included, the system extracts the raw questions.
* **The Logic:**
  1. **Regex Extraction:** It parses the actual text of the question and its associated marks (e.g., `[5 marks]`).
  2. **Smart Deduplication:** Past papers reuse questions. It runs a `difflib.SequenceMatcher` to check if a question overlaps > 85% with a previous year's question. However, if the text is identical but the *marks* are different, it is kept as a "meaningful variation" because it implies a different grading rubric.
  3. **Embedding Mapping:** It uses `SentenceTransformers` to convert the deduplicated past questions into mathematical vectors and strictly maps them against the structural topics found in Step 3. If the conceptual overlap is > 60%, the topic gains a `frequency` point.

### 6️⃣ Score Combination & Contradiction Handling
* **What happens:** The mathematical core of the pipeline.
* **The Logic:** 
  * `final_score = (alpha * frequency) + (beta * importance_score)`
  * **Contradiction Handling:** If a past paper highly features a topic, but the student's actual notes barely mention it (low importance_score), the system forcefully slashes the `final_score` by 50%. This prevents the system from blindly ranking a topic as "#1 Priority" when the student lacks the material to actually study it.
  * **Calibration Loop:** Developers can run `--calibrate` to trigger a Grid-Search loop that automatically tests dozens of `alpha` and `beta` permutations to maximize a composite evaluation score (50% Recall, 30% Precision, 20% Top-5 Ranking).

### 7️⃣ Topic Clustering
* **What happens:** "OSI Model" and "OSI 7 Layers Details" might be written as two separate chapters in the notes. We don't want the final predicted exam to have two redundant sections.
* **The Logic:** The system computes the cosine similarity across all highly scored topics. If it detects a semantic similarity > `0.75`, it aggressively **clusters** them into a single "Representative Master Chunk", taking the combined context and average scores of both items to prevent output spam.

### 8️⃣ Final Topic Ranking & Pruning
* **What happens:** We strip out the academic noise. 
* **The Logic:** The remaining clustered topics are sorted by their `final_score`. The system calculates the Mean and Standard Deviation across all topics. It sets a dynamic statistical threshold (`pruning_threshold = mean + (0.3 * std_dev)`). Any topic falling below this mathematical line is permanently dropped. 

### 9️⃣ Question Generation (Template-Based)
* **What happens:** Instead of telling an LLM "Generate some questions about this topic" (which causes catastrophic hallucination), ExamerAI uses rigid, deterministic academic templates.
* **The Logic:** Based on the weight of the topic, it generates targeted prompts:
  * **Define [Topic]** (2 marks)
  * **Explain the core concepts of [Topic]** (5 marks)
  * **Discuss and analyze [Topic] in detail** (10 marks) 
  
### 🔟 Context Retrieval (`smartRetriever.py`)
* **What happens:** Grounding the upcoming answer.
* **The Logic:** For each template-generated question, the Retriever isolates the exact snippet of text from the `StructuredDocumentBuilder` to ensure the answer is strictly sourced from the student's actual class material, completely blocking outside Internet hallucination.

### 1️⃣1️⃣ LLM Answer Formatting
* **What happens:** Local LLM processing format the textbook text into a cohesive, exam-ready answer.
* **The Logic:** ExamerAI bundles the *Template Question* + *Strict Context Snippet* and fires an HTTP POST to an active local LLM (like `deepseek-r1:7b` via port 11434).
  * **Auto-Boot:** If Ollama is asleep or completely closed, a hidden Windows background subprocess is silently spawned (`subprocess.Popen(["ollama", "serve"])`) bypassing massive API timeouts.
  * **Fallback:** If the LLM completely crashes, a deterministic Python template instantly falls in as a failsafe answer.

### 1️⃣2️⃣ Study Mode Filtering 
* **What happens:** A real-world constraint layer for exhausted students.
* **The Logic:** If a student runs `--study-time 2h`, they mathematically *cannot* study 15 complex topics. The pipeline trims the output down to precisely the top 4 representative Master Clusters. It categorizes them into explicit buckets:
  * *Priority 1 → Must study*
  * *Priority 2 → Should study* 
  * *Priority 3 → Optional*

### 1️⃣3️⃣ Explainability Layer
* **What happens:** Establishing trust. The AI must mathematically defend *why* it picked a certain topic.
* **The Logic:** The final compiled `.json` booklet injects an `explainability` node onto every topic. It prints out exactly why it was chosen (e.g. `Reason: Meets relevance threshold (Score Ratio: 0.84, Past Frequency: 2)`), ending the "black box" mystery of typical AI tools. 

---

## 💻 Tech Stack Overview

* **Extraction:** `pdfplumber`, `docx2txt`, `pytesseract`
* **Embeddings / Vectors:** `SentenceTransformers` (`all-MiniLM-L6-v2`)
* **LLM Engine:** Local `Ollama` Host (`deepseek-r1:7b`)
* **Scoring/Math:** Native `statistics`, `difflib.SequenceMatcher`

## 🚀 Terminal Execution

Ensure Python and Ollama are installed locally.

**Run System on Full Document:**
```bash
python src/mainPipeline.py --input dataSet/my_notes.pdf
```

**Run Aggressive Study Mode (Exam is Tomorrow):**
```bash
python src/mainPipeline.py --input dataSet/my_notes.pdf --study-time 1d
```

**Developer Score Calibration (Grid Search Optimization):**
```bash
python src/mainPipeline.py --input tests/temp_test_data/clean_textbook.txt --calibrate
```
