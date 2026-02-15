"""
MAIN DOCUMENT PROCESSING PIPELINE
==================================

This file runs the complete document processing pipeline:
1. Extract text from documents (PDF/DOCX/Images)
2. Clean the extracted text
3. Build hierarchical structure
4. Save outputs

You can enable/disable individual steps by commenting/uncommenting sections.
"""

import json
from pathlib import Path
from documentLoader import DocumentsExtractor
from documentsCLearing import DocumentCleaner
from documentStructure import StructuredDocumentBuilder

DOCUMENT_PATH = "../dataSet/Unit I - Introduction to E-commerce new.docx"

# Output directory path (change this to your new output folder)
OUTPUT_DIR = "../dataSet/OutputData"

def main():
    """Main pipeline execution"""
    
    # Create output directory if it doesn't exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("DOCUMENT PROCESSING PIPELINE")
    print("=" * 80)
    print()
    #raw document extract
    print("STEP 1: Extracting document...")
    print(f"Document: {DOCUMENT_PATH}")
    
    # Extract the document
    extraction_result = DocumentsExtractor.extract(DOCUMENT_PATH)
    
    print(f"✓ Extracted {len(extraction_result.raw_text)} characters")
    print(f"✓ File type: {extraction_result.file_type}")
    print(f"✓ Confidence: {extraction_result.confidence_score}")
    print()
    
    # Save raw extracted text 

    # with open(f"{OUTPUT_DIR}/01_raw_extracted.txt", "w", encoding="utf-8") as f:
    #     f.write(extraction_result.raw_text)
    # print("Raw extraction saved to: 01_raw_extracted.txt")
    # print()
    
    
    # STEP 2: TEXT CLEANING if needed manually
    # If you want to clean additional text manually:
    # cleaner = DocumentCleaner()
    # cleaning_result = cleaner.clean(
    #     some_text,
    #     remove_page_numbers=True,
    #     remove_headers_footers=True,
    #     remove_repeated_titles=True,
    #     remove_watermarks=True,
    #     normalize_bullets=True,
    #     normalize_spacing=True,
    #     fix_encoding=True
    # )
    # cleaned_text = cleaning_result.cleaned_text
    
    # Save cleaned text 
    # with open(f"{OUTPUT_DIR}/02_cleaned_text.txt", "w", encoding="utf-8") as f:
    #     f.write(extraction_result.raw_text)
    # print("Cleaned text saved to: 02_cleaned_text.txt")
    # print()
    
    
    print("STEP 2: Building hierarchical structure...")
    
    # Build structured document
    builder = StructuredDocumentBuilder()
    structured_doc = builder.build(extraction_result)
    
    print(f"✓ Found {len(structured_doc.chapters)} top-level chapters")
    
    # Count total sections
    total_sections = 0
    for chapter in structured_doc.chapters:
        total_sections += len(chapter.sections)
        for section in chapter.sections:
            total_sections += len(section.subsections)
    
    print(f"✓ Total sections: {total_sections}")
    print()
    
    print("STEP 3: Saving outputs...")
    
    output_dict = builder.to_dict(structured_doc)
    
    output_json_path = f"{OUTPUT_DIR}/structured_document.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False)
    print(f"✓ Structured JSON saved to: {output_json_path}")
    
    # Save as readable text summary
    # output_txt_path = f"{OUTPUT_DIR}/structure_summary.txt"
    # with open(output_txt_path, "w", encoding="utf-8") as f:
    #     f.write("DOCUMENT STRUCTURE SUMMARY\n")
    #     f.write("=" * 80 + "\n\n")
    #     for i, chapter in enumerate(structured_doc.chapters, 1):
    #         f.write(f"Chapter {i}: {chapter.title}\n")
    #         f.write(f"  Level: {chapter.level}\n")
    #         f.write(f"  Sections: {len(chapter.sections)}\n")
    #         f.write(f"  Lines: {chapter.line_start} - {chapter.line_end}\n\n")
    #         for j, section in enumerate(chapter.sections, 1):
    #             f.write(f"  {j}. [{section.content_type}] {section.title}\n")
    #             if section.subsections:
    #                 for k, subsection in enumerate(section.subsections, 1):
    #                     f.write(f"     {k}. [{subsection.content_type}] {subsection.title[:50]}\n")
    #         f.write("\n")
    # print(f"✓ Structure summary saved to: {output_txt_path}")
    
    print()
    
    print("-" * 80)
    print("DOCUMENT STRUCTURE OVERVIEW")
    print("-" * 80)
    print()
    
    for i, chapter in enumerate(structured_doc.chapters, 1):
        print(f"Chapter {i}: {chapter.title}")
        print(f"  Level: {chapter.level}")
        print(f"  Direct Sections: {len(chapter.sections)}")
        print(f"  Lines: {chapter.line_start} - {chapter.line_end}")
        
        if chapter.sections:
            print(f"\n  Top sections:")
            for j, section in enumerate(chapter.sections[:5], 1):
                print(f"    {j}. [{section.content_type}] {section.title[:60]}")
                if section.subsections:
                    print(f"       ({len(section.subsections)} subsections)")
            if len(chapter.sections) > 5:
                print(f"    ... and {len(chapter.sections) - 5} more sections")
        print()
    
    print("-" * 80)
    print("METADATA")
    print("-" * 80)
    for key, value in structured_doc.metadata.items():
        print(f"{key}: {value}")
    print()
    
    print("-" * 80)
    print("PIPELINE COMPLETE ✓")
    print("-" * 80)



def test_extraction_only():
    """Test only the extraction step"""
    print("Testing extraction only...\n")
    print(f"Document: {DOCUMENT_PATH}\n")
    
    result = DocumentsExtractor.extract(DOCUMENT_PATH)
    
    print(result.raw_text[:500])
    print(f"\n✓ Extracted {len(result.raw_text)} characters")
    
    # Save to file
    with open(f"{OUTPUT_DIR}/extraction_test.txt", "w", encoding="utf-8") as f:
        f.write(result.raw_text)
    print("✓ Saved to: extraction_test.txt")


def test_cleaning_only():
    """Test only the cleaning step"""
    print("Testing cleaning only...\n")
    print(f"Document: {DOCUMENT_PATH}\n")
    
    # First extract
    result = DocumentsExtractor.extract(DOCUMENT_PATH)
#
    # cleaner = DocumentCleaner()
    # cleaning_result = cleaner.clean(result.raw_text)
    
    print(f" Cleaned {len(result.raw_text)} characters")
    print(f" Warnings: {result.warnings}")


def test_structure_only():
    """Test only the structure building step"""
    print("Testing structure building only...\n")
    print(f"Document: {DOCUMENT_PATH}\n")
    
    # Extract
    result = DocumentsExtractor.extract(DOCUMENT_PATH)
    
    # Build structure
    builder = StructuredDocumentBuilder()
    structured_doc = builder.build(result)
    
    print(f"✓ Found {len(structured_doc.chapters)} chapters")
    for chapter in structured_doc.chapters:
        print(f"  • {chapter.title} ({len(chapter.sections)} sections)")



if __name__ == "__main__":
    # Run the full pipeline
    main()
    
    # Or test individual components (uncomment to enable):
    #test_extraction_only()
    # test_cleaning_only()
    # test_structure_only()
