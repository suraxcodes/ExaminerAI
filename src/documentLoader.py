import os               
import json         
from pathlib import Path 
from dataclasses import dataclass
import sys
from PIL import Image
from unittest import result
from docx import Document
from pypdf import PdfReader
import pytesseract

from documentsCLearing import DocumentCleaner


if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@dataclass
class ExtractionResult:
    raw_text: str
    file_type: str
    page_count: int 
    page_mapping: list 
    confidence_score: float 
    warnings: list 
    formatting_notes: dict 
    line_metadata: dict = None  # NEW: {line_index: {"bold_count": X, ...}}

# Inside DocumentLoader class:
class DocumentDetector:
    @staticmethod
    def detect_file_type(file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix == ".docx":
            return "docx"
        elif suffix == ".pdf":
            return "pdf"
        elif suffix in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"]:
            return "image"
        return "unknown"

class DocumentsExtractor:
    @staticmethod
    def extract(file_path):
        detector = DocumentDetector()
        file_type = detector.detect_file_type(file_path)
        
        if file_type == "docx":
            return DocxExtractor.extract(file_path)
        elif file_type == "pdf":
            # Assuming PDFExtractor logic exists or placeholder
            all_text, page_info, confidence, warnings, formatting, page_count = PDFExtractor.extract(file_path)
            return ExtractionResult(
                raw_text=all_text, file_type="pdf", page_count=page_count,
                page_mapping=page_info, confidence_score=confidence,
                warnings=warnings, formatting_notes=formatting, line_metadata={}
            )
        elif file_type == "image":
            all_text, page_info, confidence, warnings, formatting, page_count = ImageExtractor.extractImaege(file_path)
            return ExtractionResult(
                raw_text=all_text, file_type="image", page_count=page_count,
                page_mapping=page_info, confidence_score=confidence,
                warnings=warnings, formatting_notes=formatting, line_metadata={}
            )
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

class PDFExtractor:
    @staticmethod
    def extract(file_path):
        warnings = []
        try:
            pdf_reader = PdfReader(file_path)
            all_text = ""
            page_info = []
            total_confidence = 0.0
            num_pages = len(pdf_reader.pages)

            for page_number, page in enumerate(pdf_reader.pages, 1):
                char_start = len(all_text)
                page_text = page.extract_text() or ""
                all_text += page_text + "\n\n"
                char_end = len(all_text)
                confidence = 0.95 if page_text.strip() else 0.5
                total_confidence += confidence
                page_info.append({
                    "page_number": page_number, "text": page_text,
                    "confidence": confidence, "char_start": char_start, "char_end": char_end
                })

            avg_confidence = total_confidence / num_pages if num_pages > 0 else 0.0
            return all_text, page_info, avg_confidence, warnings, {}, num_pages
        except Exception as e:
            return f"[PDF error: {e}]", [], 0.0, [str(e)], {}, 0

class ImageExtractor:
    @staticmethod
    def extractImaege(file_path):
        warnings = []
        try:
            image = Image.open(file_path)
            image_extract_text = pytesseract.image_to_string(image)
            try:
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                valid_confidences = [int(c) for c in ocr_data['conf'] if int(c) > 0]
                avg_confidence = (sum(valid_confidences) / len(valid_confidences)) / 100.0 if valid_confidences else 0.7
            except:
                avg_confidence = 0.7
            page_info = [{"page_number": 1, "char_start": 0, "char_end": len(image_extract_text), "ocr_confidence": avg_confidence}]
            if avg_confidence < 0.7:
                warnings.append("Low OCR confidence, text may be inaccurate.")
            return image_extract_text, page_info, avg_confidence, warnings, {}, 1
        except Exception as e:
            return f"[ImageExtractor error: {e}]", [], 0.0, [str(e)], {}, 0

class DocxExtractor:
    @staticmethod
    def extract(file_path):
        doc = Document(file_path)
        all_text = ""
        line_metadata = {}
        
        for i, paragraph in enumerate(doc.paragraphs):
            para_text = paragraph.text
            bold_words = [run.text for run in paragraph.runs if run.bold]
            
            # This is the "DNA" of each line
            line_metadata[i] = {
                "bold_count": len(bold_words),
                "is_list": "•" in para_text or paragraph.style.name.startswith("List"),
                "text": para_text
            }
            all_text += para_text + "\n"

        return ExtractionResult(
            raw_text=all_text,
            file_type="docx",
            page_count=1,
            line_metadata=line_metadata,
            page_mapping=[], confidence_score=1.0, warnings=[], formatting_notes={}
        )
    #format and save 
class ResultFormatter:
        """format the rusults and save to files """


        def format_text_with_mapping(result):
            """
            Take the results and format them nicely with page markers

            Creates a report that shows:
            - File type
            - Number of pages
            - Quality score
            - Any warnings
            - The text with page markers
            """

            output = "=" * 80 + "\n"
            output += "DOCUMENT EXTRACTION REPORT\n"
            output += "=" * 80 + "\n\n"

            output += f"File Type: {result.file_type.upper()}\n"
            output += f"Pages: {result.page_count}\n"
            output += f"Quality: {result.confidence_score:.1%}\n"

            if result.warnings:
                output += "\nWARNINGS:\n"
                for warning in result.warnings:
                    output += f"  {warning}\n"

            output += "\n" + "=" * 80 + "\n"
            output += "EXTRACTED TEXT\n"
            output += "=" * 80 + "\n\n"
            output += result.raw_text

            return output
        
        def save_json_mapping(result, output_path):
            """ Save the page mapping info to a JSON file
            This is useful if you want to use the data in another program
            """
            
            # Create the data to save
            data = {
                "metadata": {
                    "file_type": result.file_type,
                    "page_count": result.page_count,
                    "confidence": result.confidence_score,
                    "warnings": result.warnings
                },
                "page_mapping": result.page_mapping,
                "text_summary": {
                    "total_characters": len(result.raw_text),
                    "total_lines": len(result.raw_text.split('\n')),
                    "total_words": len(result.raw_text.split())
                }
            }
            with open(output_path,'w',encoding='utf-8') as f :
                json.dump(data,f,indent=4)
            print (f"Page mapping saved to {output_path}")

def main():


    if len(sys.argv) < 2:
            print("DOCUMENT TEXT EXTRACTOR")
            print("=" * 50)
            print("\nUsage: python document_extractor.py <file> [output_file]")
            print("\nSupported files: PDF, DOCX, JPG, PNG, BMP, GIF, TIFF")
            print("\nExamples:")
            print("  python document_extractor.py report.pdf")
            print("  python document_extractor.py document.docx output.txt")
            print("\nIf you dont give output file ,result shown on screem. ")
            sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"\n Extracting text from: {input_file}\n")

    result = DocumentsExtractor.extract(input_file)

    formatted_result = ResultFormatter.format_text_with_mapping(result)

    if output_file:
        with open(output_file,'w',encoding='utf-8') as f:
            f.write(formatted_result)

        print(f"Formatted result saved to {output_file}")
    else:
        print(formatted_result)

if __name__=="__main__":
    main()

    # result = DocumentsExtractor.extract("../dataSet/Fundamentals_of_Cybersecurity.pdf")
    # print(result.raw_text)
    
    # with open("../dataSet/OutputData/output.txt", "w", encoding="utf-8") as f:
    #     f.write(result.raw_text)
    # print("\nOutput saved to: ../dataSet/OutputData/output.txt")
