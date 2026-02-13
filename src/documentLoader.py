import os           # For working with files and folders     
import json         # For saving data in JSON format
from pathlib import Path 
from dataclasses import dataclass
from tkinter import Image
from unittest import result
from xml.dom.minidom import Document 
from pypdf import PdfReader
import pytesseract
#data container for document 
@dataclass
class ExtractionResult:
    """it going to contain the extracted text """
    raw_text:str
    file_type:str
    page_count:int # of pages document
    page_mapping:list # list of page numbers and with their corresponding text
    confidence_score:float 
    Warnings:list 
    formatting_notes:dict 

#file detection 
file_path = r"C:\Users\Sarvesh\Documents\2025Projects\examerAi\dataSet\sample.pdf"
class DocumentDetector:
    """This class will detect file type."""

    def detect_file_type(file_path):
        ext = Path(file_path).suffix.lower()

        type_map = {
                '.pdf': "pdf",
                '.docx': "docx",
                '.doc': "doc",
                '.jpg': "image",
                '.jpeg': "image",
                '.png': "image",
                '.bmp': "image",
                '.tiff': "image",
                '.gif': "image",
                }
        return type_map.get(ext, "unknown")
    
    def validated_file(file_path):
        """ check for file existence and valid type"""
        #check for file exist 
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        #check file is acce3seble
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"File is not readable: {file_path}")
        
        file_path = DocumentDetector.detect_file_type(file_path)
        if file_path =="unknown":
            return False,f"Unsupported file type: {file_path}"
        
        return True ," file is good to Gooooooooo"
    
class PDFExtractor:
    """"pdf extract logic will go here"""
    def extract(file_path):
        """ will return text ,page count , page mapping , confidence score , warnings, formatting notes"""

        warmings = []
        

        try :
            pdf_reader = PdfReader(file_path)

            all_text = ""
            page_info = []
            total_confidence = 0.0

            #how many pages in pdf
            num_pages = len(pdf_reader.pages)

            for page_number,page in enumerate(pdf_reader.pages,1):
                
                char_start = len(all_text)
                # Extract text from this page
                page_text = page.extract_text()

                if page_text is None :
                    page_text=""

                all_text +=page_text + "\n\n" 

                char_end = len(all_text)

                if len(page_text.strip()) > 0:
                    confidence = 0.95
                else:
                    confidence = 0.5

                total_confidence += confidence

                page_info.append(
                    {
                        "page_number": page_number,
                        "text": page_text,
                        "confidence": confidence,
                        "char_start": char_start,
                        "char_end": char_end
                    }
                )

            avg_confidence = total_confidence / num_pages if num_pages > 0 else 0.0

            return all_text, num_pages, page_info, avg_confidence, warmings, {}
        
        except Exception as e:
            return f"[PDF error: {e}]"

# document loader class
class DocumentLoader:
    """extract text from doucment """

    def extract(file_path):
        """ main method to extract text from document"""
            

        
        try:
            doc = Document(file_path)

            all_text = ""
            page_info = []

            formatting = {
                "bold_count": 0,
                "italic_count": 0,
                "heading": 0,
                "list_count": 0,
            } 

            #go in each paragraph in document
            for para_index,paragraph in enumerate(doc.paragraphs):

                char_start = len(all_text)

                para_text = paragraph.text

                style_name = paragraph.style.name
                is_heading = "Heading" in style_name
# If it's a heading, add a marker so we know it's special
                if is_heading:
                    formatting["heading"]+=1

                    try:
                        level = int(style_name[-1])
                    except:
                        level = 0
                        para_text = f"[HEADING]{level} {para_text}"
         # Check if this is a list item (bullet point)        
                if style_name.startswith("List"):
                    formatting["list"]+=1
                    para_text = f"[LIST] {para_text}"
 # Check for bold and italic text
                for run in paragraph.runs:
                    if run.bold:
                        formatting["bold_count"]+=1
                    if run.italic:
                        formatting["italic_count"]+=1

                all_text += para_text + "\n\n"

                char_end = len(all_text)

                page_info.append(
                    {
                        "elements": para_index,
                        "is_heading": is_heading,
                        "char_start": char_start,
                        "char_end": char_end,
                        "style": style_name
                    }
                )

                confidence = 0.98

                return all_text ,page_info,confidence,formatting

        except Exception as e :
            return f"[DocumentLoader error: {e}]"    

## extract text from image using OCR
class ImageExtractor:
    """extract text from image using OCR"""

    def extractImaege(file_path):
        """ take image and extract text from it usess orc """

        try:
            image = Image.open(file_path)
            image_extract_text = pytesseract.image_to_string(image)

# Try to get confidence score
            try:
                ocr_data = pytesseract.image_to_data(image,Output_type='dict')

                confidence = (int(c) for c in ocr_data['conf'] if int(c) > 0)
                avg_confidence = sum(confidence) / len(confidence) if confidence else 0.0

                confidence = avg_confidence//100.0

            except:
                confidence = 0.7

#store page info 
            page_info =[{
                "page_number": 1,
                "char_start": 0,
                "char_end": len(image_extract_text),
                "__path__ocr_confidence": confidence
            }]    

            if confidence < 0.7:
                warnings = ["Low OCR confidence, text may be inaccurate."]
            
            return image_extract_text,page_info,confidence,warnings,
        except Exception as e:
            return f"[ImageExtractor error: {e}]"   
        
class DocumentsExtractor:
    """this class will be the main entry point for document
    1. Checks if file is valid
    2. Figures out what type it is
    3. Sends it to the right extractor
    4. Returns the results"""

    def extract(file_path):
        # Step 1 check if file is okayyyyy
        is_valid , validation_message = DocumentDetector.validated_file(file_path)

        if not is_valid:
            print(validation_message)

            return ExtractionResult(
                raw_text="",
                file_type="unknown",
                page_count=0,
                page_mapping=[],
                confidence=0.0,
                warnings=[validation_message],
                formatting_notes={}
            )
        
        # Step 2 figure out file type
        file_type = DocumentDetector.detect_file_type(file_path)

        if file_type =="pdf":
            text,mapping,confidence,warnings = PDFExtractor.extract(file_path)
        elif file_type == "docx" or file_type == "doc":
            text,mapping,confidence,warnings = DocumentLoader.extract(file_path)
        elif file_type == "image":
            text,mapping,confidence,warnings = ImageExtractor.extractImaege(file_path)   
        else:
            #unknow filew type
            return ExtractionResult(
                raw_text="",    
                file_type=file_type,
                page_count=0,
                page_mapping=[],
                confidence=0.0,
                warnings=[f"Unsupported file type: {file_type}"],
                formatting_notes={}
            )
        
        #step 4 check if extraction was successful
        if confidence < 0 and len(text.strip()) > 0:
            warnings.append(f"⚠️ Low confidence ({confidence:.1%}). Check text carefully.")
        if len(text.strip()) == 0:
            warnings.append("⚠️ No text extracted. Check if the document is empty or if there was an extraction issue.")

        return ExtractionResult(
                    raw_text=text,
                    file_type=file_type,
                    page_count=len(mapping),
                    page_mapping=mapping,
                    confidence=confidence,
                    warnings=warnings,
                    formatting_notes={}
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

            # Create the report
            output = "=" * 80 + "\n"
            output += "DOCUMENT EXTRACTION REPORT\n"
            output += "=" * 80 + "\n\n"

            # Add summary info
            output += f"File Type: {result.file_type.upper()}\n"
            output += f"Pages: {result.page_count}\n"
            output += f"Quality: {result.confidence:.1%}\n"

            # Add any warnings
            if result.warnings:
                output += "\nWARNINGS:\n"
                for warning in result.warnings:
                    output += f"  {warning}\n"

            # Add the extracted text
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
                    "confidence": result.confidence,
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
        
