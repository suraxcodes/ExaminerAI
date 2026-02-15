import re 
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class CleaningResult:
    """how result od ducments will be """
    original_text:str
    cleaned_text:str
    removed_items:dict
    issues_fixed:list[str]
    statistics: Dict             
    
class PageNumberRemover:
    """remove page numbers from text"""
    
    def find_page_numbers(text:str)->list[dict]:
        """find page numbers in text
        look for patteran like page 2 page 1 ,1,2,3"""
        
        page_numbers = []
        lines = text.split('\n')

        page_pattern = re.compile(r'^\s*[Pp]age\s+(\d+)\s*$')
        number_pattern = re.compile(r'^\s*(\d+)\s*$')
        dash_pattern = re.compile(r'^\s*[-–—]+\s*$')
        bracket_pattern = re.compile(r'^\s*\[\d+\]\s*$')
        
        for line_num,line in enumerate(lines):
            if page_pattern.match(line):
                page_numbers.append({
                    'pattern': 'page_label',
                    'line_number': line_num,
                    'text': line.strip()
                })
                continue
            if dash_pattern.match(line):
                page_numbers.append({
                    'pattern':'dash_format',
                    'line_number':line_num,
                    'text':line.strip()
                })
                continue
            if bracket_pattern.match(line):
                page_numbers.append({
                    'pattern':'bracket_format',
                    'line_number':line_num,
                    'text':line.strip()
                })
                continue

            match = number_pattern.match(line)
            if match:
                num = match.group(1)
                if len(num) <=3 and int(num) <1000:
                    page_numbers.append({
                        'pattern':'standalone_number',
                        'line_number':line_num,
                        'text':num
                    })
        return page_numbers

    @staticmethod
    def remove_page_numbers(text: str) -> tuple:
        """remove page number from text """
        page_numbers = PageNumberRemover.find_page_numbers(text)

        if not page_numbers:
            return text, 0

        lines =text.split('\n')

        for page_info in reversed(page_numbers):
            lines.pop(page_info['line_number'])
        
        cleaned_text = '\n'.join(lines)
        
        return cleaned_text, len(page_numbers)

class HeaderFooterRemover:
    """remove headers and footers from text"""
    
    @staticmethod
    def find_headers_footers(text: str) -> Dict:
        """
        Find potential headers and footers
        Repeated content
        At top or bottom of pages
        often contain document title or chapter name
        """
        
        lines = text.split('\n')
        line_counts = {}
        
        # Count how often each line appears
        for line in lines:
            stripped = line.strip()
            if 10 < len(stripped) < 200:  
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        # Find repeated lines (potential headers/footers)
        repeated_lines = {
            line: count for line, count in line_counts.items()
            if count >= 2
        }
        
        return {
            'repeated_lines': repeated_lines,
            'candidates': list(repeated_lines.keys())
        }
    
    @staticmethod
    def remove_headers_footers(text: str, 
                               threshold: int = 2) -> tuple:
        """
        Remove headers and footers that appear multiple times
            text: The text to clean
            threshold: Minimum appearances to consider as header/footer
        """
        
        headers_footers = HeaderFooterRemover.find_headers_footers(text)
        repeated = headers_footers['repeated_lines']
        
        to_remove = {
            line: count for line, count in repeated.items()
            if count >= threshold
        }
        
        if not to_remove:
            return text, 0
        
        lines = text.split('\n')
        cleaned_lines = []
        removed_count = 0
        
        for line in lines:
            if line.strip() in to_remove:
                removed_count += 1
            else:
                cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        return cleaned_text, removed_count
    
class RepeatedTitleRemover:
    """Remove repeated chapter titles and section headers"""
    
    @staticmethod
    def find_repeated_titles(text: str) -> List[str]:
        """
        Find titles/headings that appear multiple times
        [HEADING 1]   Chapter 1: Introduction
        Introduction text here...
        [HEADING 1] Chapter 1: Introduction
        More text... """
        
        heading_pattern = re.compile(r'\[HEADING\s+\d+\]\s+(.+)')
        
        headings = {}
        
        for line in text.split('\n'):
            match = heading_pattern.match(line)
            if match:
                title = match.group(1).strip()
                headings[title] = headings.get(title, 0) + 1
        
        # Find repeated headings
        repeated = [title for title, count in headings.items() if count > 1]
        
        return repeated
    
    @staticmethod
    def remove_repeated_titles(text: str) -> tuple:
        """
        Remove repeated heading lines
        
        Keeps first occurrence, removes subsequent ones
        
        Returns: (cleaned_text, titles_removed)
        """
        
        repeated_titles = RepeatedTitleRemover.find_repeated_titles(text)
        
        if not repeated_titles:
            return text, 0
        
        lines = text.split('\n')
        cleaned_lines = []
        seen_titles = set()
        removed_count = 0
        
        for line in lines:
            # Check if line is a repeated heading
            is_repeated_heading = False
            for title in repeated_titles:
                if title in line and '[HEADING' in line:
                    if title in seen_titles:
                        # We've seen this title before, remove it
                        removed_count += 1
                        is_repeated_heading = True
                        break
                    else:
                        # First time seeing this title, keep it
                        seen_titles.add(title)
            
            if not is_repeated_heading:
                cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines)
        
        return cleaned_text, removed_count

class WatermarkRemover:
    """Remove watermarks and other noise patterns"""
    
    # Common watermark patterns
    WATERMARK_PATTERNS = [
        r'©\s*20\d{2}',                    
        r'confidential',                    
        r'draft',                           
        r'internal.*only',                  
        r'not\s+for\s+distribution',       
        r'proprietary',                     
        r'www\.[a-zA-Z0-9.-]+\.[a-z]{2,}', 
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  
    ]
    
    @staticmethod
    def find_watermarks(text: str) -> List[Dict]:
        """
        Find potential watermarks in text
        """
        
        watermarks = []
        
        for i, pattern in enumerate(WatermarkRemover.WATERMARK_PATTERNS):
            matches = re.finditer(
                pattern,
                text,
                re.IGNORECASE
            )
            
            for match in matches:
                watermarks.append({
                    'text': match.group(0),
                    'pattern_index': i,
                    'position': match.start()
                })
        
        return watermarks
    
    @staticmethod
    def remove_watermarks(text: str, 
                         remove_emails: bool = False,
                         remove_urls: bool = False) -> tuple:
        """
        Remove watermarks from text
        """
        
        cleaned_text = text
        removed_count = 0
        
        # List of patterns to remove (conservative approach)
        patterns_to_remove = [
            r'©\s*20\d{2}',                      
            r'(?i)confidential',                 
            r'(?i)draft',                        
            r'(?i)internal\s+only',              
            r'(?i)not\s+for\s+distribution',
            r'(?i)proprietary',                  
        ]
        
        # Optionally  URLs and emails
        if remove_urls:
            patterns_to_remove.append(
                r'www\.[a-zA-Z0-9.-]+\.[a-z]{2,}'
            )
        
        if remove_emails:
            patterns_to_remove.append(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            )
        
        # Apply each pattern
        for pattern in patterns_to_remove:
            matches = list(re.finditer(pattern, cleaned_text))
            removed_count += len(matches)
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        return cleaned_text, removed_count

class BulletNormalizer:
    """Normalize different bullet point styles"""
    
    # Common bullet markers
    BULLET_PATTERNS = [
        (r'^[\s]*[•·▪▸▹►][\s]+', '• '),      
        (r'^[\s]*[-–—][\s]+', '• '),          
        (r'^[\s]*\*[\s]+', '• '),
        (r'^[\s]*[+]+[\s]+', '• '),            
        (r'^[\s]*\d+\)[\s]+', '• '),           
        (r'^[\s]*\([a-z]\)[\s]+', '• '),       
        (r'^[\s]*[a-z]\)[\s]+', '• '),
    ]
    
    @staticmethod
    def normalize_bullets(text: str) -> tuple:
        """
        Normalize all bullet point styles to consistent format
        
        """
        
        lines = text.split('\n')
        normalized_lines = []
        normalized_count = 0
        
        for line in lines:
            original_line = line
            
            # Try each bullet pattern
            for pattern, replacement in BulletNormalizer.BULLET_PATTERNS:
                if re.match(pattern, line):
                    # This line has a bullet
                    line = re.sub(pattern, replacement, line)
                    if line != original_line:
                        normalized_count += 1
                    break
            
            normalized_lines.append(line)
        
        normalized_text = '\n'.join(normalized_lines)
        
        return normalized_text, normalized_count


class LineSpacingNormalizer:
    """Normalize line spacing and whitespace"""
    
    @staticmethod
    def normalize_spacing(text: str, 
                         remove_extra_blank_lines: bool = True,
                         normalize_indentation: bool = True) -> tuple:
        """
        Normalize line spacing and indentation
        """
        
        lines = text.split('\n')
        normalized_lines = []
        issues_fixed = 0
        
        previous_blank = False
        
        for line in lines:
            original_line = line
            
            # Normalize indentation (convert tabs to spaces)
            if normalize_indentation:
                if '\t' in line:
                    line = line.replace('\t', '    ')  
                    issues_fixed += 1
            
            is_blank = len(line.strip()) == 0
            
            if remove_extra_blank_lines:
                if is_blank and previous_blank:
                    continue  
                previous_blank = is_blank
            
            line = line.rstrip()
            
            if line != original_line:
                issues_fixed += 1
            
            normalized_lines.append(line)
        
        while normalized_lines and len(normalized_lines[-1].strip()) == 0:
            normalized_lines.pop()
            issues_fixed += 1
        
        normalized_text = '\n'.join(normalized_lines)
        
        return normalized_text, issues_fixed

class EncodingFixer:
    """Fix encoding issues in text"""
    
    # Common encoding problems and replacements
    ENCODING_FIXES = [
        (r'“|”', '"'),
        (r'‘|’', "'"),
        (r'—', '--'),
        (r'–', '-'),
        (r'…', '...'),
        (r'[\x80-\x9F]', ''),  
    ]
    
    @staticmethod
    def fix_encoding(text: str) -> tuple:
        """
        Fix common encoding issues
        """
        
        cleaned_text = text
        issues_fixed = 0
        
        for pattern, replacement in EncodingFixer.ENCODING_FIXES:
            matches = len(re.findall(pattern, cleaned_text))
            if matches > 0:
                issues_fixed += matches
                cleaned_text = re.sub(pattern, replacement, cleaned_text)
        
        return cleaned_text, issues_fixed
    
    @staticmethod
    def fix_common_typos(text: str) -> tuple:
        """
        Fix common encoding-related typos
        
        Examples:
        - "aﬀ" → "af"
        - Multiple spaces → Single space
        - Line breaks in middle of words
        """
        
        cleaned_text = text
        issues_fixed = 0
        
        matches = len(re.findall(r' {2,}', cleaned_text))
        if matches > 0:
            issues_fixed += matches
            cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
        
        ligature_fixes = [
            ('ﬁ', 'fi'),
            ('ﬂ', 'fl'),
            ('ﬀ', 'ff'),
            ('ﬃ', 'ffi'),
            ('ﬄ', 'ffl'),
        ]
        
        for ligature, replacement in ligature_fixes:
            matches = len(re.findall(ligature, cleaned_text))
            if matches > 0:
                issues_fixed += matches
                cleaned_text = cleaned_text.replace(ligature, replacement)
        
        return cleaned_text, issues_fixed


class DocumentCleaner:
    """Main class for document cleaning"""
    
    def __init__(self):
        """Initialize all cleaners"""
        self.page_number_remover = PageNumberRemover()
        self.header_footer_remover = HeaderFooterRemover()
        self.repeated_title_remover = RepeatedTitleRemover()
        self.watermark_remover = WatermarkRemover()
        self.bullet_normalizer = BulletNormalizer()
        self.line_spacing_normalizer = LineSpacingNormalizer()
        self.encoding_fixer = EncodingFixer()
    
    def clean(self, text: str, 
             remove_page_numbers: bool = True,
             remove_headers_footers: bool = True,
             remove_repeated_titles: bool = True,
             remove_watermarks: bool = True,
             normalize_bullets: bool = True,
             normalize_spacing: bool = True,
             fix_encoding: bool = True) -> CleaningResult:
        """
        Clean document text
        
        Removes noise and normalizes content
        
        Returns: CleaningResult with cleaned text and statistics
        """
        
        original_text = text
        cleaned_text = text
        removed_items = {}
        issues_fixed = []
        
        print("Starting document cleaning...\n")
        
        # Step 1: Remove page numbers
        if remove_page_numbers:
            print(" Removing page numbers...")
            cleaned_text, count = self.page_number_remover.remove_page_numbers(
                cleaned_text
            )
            if count > 0:
                removed_items['page_numbers'] = count
                issues_fixed.append(f"Removed {count} page numbers")
                print(f"     Removed {count} page numbers")
        
        # Step 2: Remove headers/footers
        if remove_headers_footers:
            print(" Removing headers/footers...")
            cleaned_text, count = self.header_footer_remover.remove_headers_footers(
                cleaned_text
            )
            if count > 0:
                removed_items['headers_footers'] = count
                issues_fixed.append(f"Removed {count} header/footer lines")
                print(f"     Removed {count} header/footer lines")
        
        # Step 3: Remove repeated titles
        if remove_repeated_titles:
            print(" Removing repeated titles...")
            cleaned_text, count = self.repeated_title_remover.remove_repeated_titles(
                cleaned_text
            )
            if count > 0:
                removed_items['repeated_titles'] = count
                issues_fixed.append(f"Removed {count} repeated titles")
                print(f"Removed {count} repeated titles")
        
        # Step 4: Remove watermarks
        if remove_watermarks:
            print("Removing watermarks...")
            cleaned_text, count = self.watermark_remover.remove_watermarks(
                cleaned_text
            )
            if count > 0:
                removed_items['watermarks'] = count
                issues_fixed.append(f"Removed {count} watermarks")
                print(f"Removed {count} watermarks")
        
        # Step 5: Normalize bullets
        if normalize_bullets:
            print("Normalizing bullet points...")
            cleaned_text, count = self.bullet_normalizer.normalize_bullets(
                cleaned_text
            )
            if count > 0:
                removed_items['bullets_normalized'] = count
                issues_fixed.append(f"Normalized {count} bullet points")
                print(f"Normalized {count} bullet points")
        
        # Step 6: Normalize spacing
        if normalize_spacing:
            print("Normalizing line spacing...")
            cleaned_text, count = self.line_spacing_normalizer.normalize_spacing(
                cleaned_text
            )
            if count > 0:
                removed_items['spacing_normalized'] = count
                issues_fixed.append(f"Fixed {count} spacing issues")
                print(f"Fixed {count} spacing issues")
        
        # Step 7: Fix encoding
        if fix_encoding:
            print("Fixing encoding issues...")
            cleaned_text, count = self.encoding_fixer.fix_encoding(cleaned_text)
            if count > 0:
                removed_items['encoding_fixed'] = count
                issues_fixed.append(f"Fixed {count} encoding issues")
                print(f"Fixed {count} encoding issues")
            
            cleaned_text, count = self.encoding_fixer.fix_common_typos(
                cleaned_text
            )
            if count > 0:
                removed_items['typos_fixed'] = count
                issues_fixed.append(f"Fixed {count} typos")
                print(f"Fixed {count} typos")
        
        print("\n Document cleaning complete!\n")
        
        # Calculate statistics
        statistics = {
            'original_length': len(original_text),
            'cleaned_length': len(cleaned_text),
            'characters_removed': len(original_text) - len(cleaned_text),
            'original_lines': len(original_text.split('\n')),
            'cleaned_lines': len(cleaned_text.split('\n')),
            'lines_removed': (len(original_text.split('\n')) - 
                            len(cleaned_text.split('\n')))
        }
        
        return CleaningResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            removed_items=removed_items,
            issues_fixed=issues_fixed,
            statistics=statistics
        )


class CleaningOutputFormatter:
    """Format cleaning results"""
    
    @staticmethod
    def format_summary(result: CleaningResult) -> str:
        """Format a cleaning summary"""
        
        summary = "=" * 80 + "\n"
        summary += "DOCUMENT CLEANING REPORT\n"
        summary += "=" * 80 + "\n\n"
        
        # Statistics
        summary += "STATISTICS:\n"
        summary += f"  Original length: {result.statistics['original_length']:,} chars\n"
        summary += f"  Cleaned length: {result.statistics['cleaned_length']:,} chars\n"
        summary += f"  Removed: {result.statistics['characters_removed']:,} chars "
        summary += f"({100*result.statistics['characters_removed']/max(1,result.statistics['original_length']):.1f}%)\n"
        summary += f"\n"
        summary += f"  Original lines: {result.statistics['original_lines']}\n"
        summary += f"  Cleaned lines: {result.statistics['cleaned_lines']}\n"
        summary += f"  Removed: {result.statistics['lines_removed']} lines\n"
        summary += "\n"
        
        # Items removed
        if result.removed_items:
            summary += "ITEMS REMOVED:\n"
            for item_type, count in result.removed_items.items():
                summary += f"  • {item_type}: {count}\n"
            summary += "\n"
        
        # Issues fixed
        if result.issues_fixed:
            summary += "ISSUES FIXED:\n"
            for issue in result.issues_fixed:
                summary += f"  • {issue}\n"
            summary += "\n"
        
        summary += "=" * 80 + "\n"
        
        return summary
    
    @staticmethod
    def format_comparison(result: CleaningResult, 
                         show_lines: int = 10) -> str:
        """Show before/after comparison"""
        
        comparison = "=" * 80 + "\n"
        comparison += "BEFORE/AFTER COMPARISON\n"
        comparison += "=" * 80 + "\n\n"
        
        original_lines = result.original_text.split('\n')[:show_lines]
        cleaned_lines = result.cleaned_text.split('\n')[:show_lines]
        
        comparison += "ORIGINAL (first 10 lines):\n"
        comparison += "-" * 80 + "\n"
        for i, line in enumerate(original_lines, 1):
            comparison += f"{i:2d}: {line[:76]}\n"
        
        comparison += "\n"
        comparison += "CLEANED (first 10 lines):\n"
        comparison += "-" * 80 + "\n"
        for i, line in enumerate(cleaned_lines, 1):
            comparison += f"{i:2d}: {line[:76]}\n"
        
        comparison += "\n" + "=" * 80 + "\n"
        
        return comparison

# def example_usage():

    
    # # Clean the document
    # cleaner = DocumentCleaner()
    # result = cleaner.clean(example_text)
    
    # # Display results
    # print(CleaningOutputFormatter.format_summary(result))
    # print("\n")
    # print(CleaningOutputFormatter.format_comparison(result))
    # print("\n")
    # print("CLEANED TEXT:")
    # print("=" * 80)
    # print(result.cleaned_text)
    # print("=" * 80)


if __name__ == "__main__":
    print("DOCUMENT CLEANER\n")
    example_usage()