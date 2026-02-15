import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from documentLoader import ExtractionResult


@dataclass
class Topic:
    """Represents a topic within a chapter"""
    title: str
    level: int
    content: str
    content_type: str  
    line_start: int
    line_end: int
    subsections: List['Topic'] = field(default_factory=list)


@dataclass
class Chapter:
    """Represents a chapter/section in the document"""
    title: str
    level: int 
    sections: List[Topic] = field(default_factory=list)  
    line_start: int = 0
    line_end: int = 0


@dataclass
class StructuredDocument:
    """Final structured output with true hierarchy"""
    chapters: List[Chapter]
    metadata: Dict


class HeadingDetector:
    """Detect headings from various formats"""
    
    # Pattern for numbered headings (1., 1.1, 1.1.1, etc.)
    NUMBERED_HEADING = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)$')
    
    # Pattern for [HEADING N] markers
    HEADING_MARKER = re.compile(r'^\[HEADING\s+(\d+)\]\s*(.+)$')
    
    # Pattern for common heading keywords
    HEADING_KEYWORDS = [
        r'^(?:chapter|unit|section|part)\s+\d+',
        r'^(?:introduction|conclusion|summary|overview)',
        r'^(?:appendix|references|bibliography)',
    ]
    
    @staticmethod
    def detect_heading(line: str, prev_line: str = '', next_line: str = '', 
                       formatting_info: Dict = None) -> Optional[Dict]:
        """
        Detect if a line is a heading and return its info
        
        Args:
            line: The line to check
            prev_line: Previous line (for blank line check)
            next_line: Next line (for blank line check)
            formatting_info: Optional formatting metadata from DOCX
        
        Returns: {
            'type': 'numbered'|'marker'|'keyword'|'formatted',
            'level': int,
            'title': str,
            'original': str
        } or None
        """
        
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            return None
        
        # Priority 1: Check formatting_info from DOCX (most reliable)
        if formatting_info and 'is_heading' in formatting_info:
            if formatting_info['is_heading']:
                # Extract level from style name if available
                level = formatting_info.get('heading_level', 2)
                return {
                    'type': 'formatted',
                    'level': level,
                    'title': line_stripped,
                    'original': line_stripped
                }
        
        # Priority 2: Check for [HEADING N] markers
        marker_match = HeadingDetector.HEADING_MARKER.match(line_stripped)
        if marker_match:
            level = int(marker_match.group(1))
            title = marker_match.group(2).strip()
            return {
                'type': 'marker',
                'level': level,
                'title': title,
                'original': line_stripped
            }
        
        # Priority 3: Check for numbered headings (1., 1.1, etc.)
        numbered_match = HeadingDetector.NUMBERED_HEADING.match(line_stripped)
        if numbered_match:
            number = numbered_match.group(1)
            title = numbered_match.group(2).strip()
            # Level = number of dots + 1 (1. = level 1, 1.1 = level 2)
            level = number.count('.') + 1
            return {
                'type': 'numbered',
                'level': level,
                'title': title,
                'original': line_stripped,
                'number': number
            }
        
        # Priority 4: Check for keyword headings (stricter now)
        for pattern in HeadingDetector.HEADING_KEYWORDS:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                return {
                    'type': 'keyword',
                    'level': 1,
                    'title': line_stripped,
                    'original': line_stripped
                }
        
        # Remove inferred heading logic - too unreliable
        return None


class ContentTypeIdentifier:
    """Identify content types (definitions, lists, bullet blocks)"""
    
    # Expanded definition patterns
    DEFINITION_PATTERNS = [
        re.compile(r'^([A-Z][^:]{1,50}):\s+(.+)$'),
        re.compile(r'^([A-Z][^.]{1,50})\s+is\s+defined\s+as\s+(.+)$', re.IGNORECASE),
        re.compile(r'^([A-Z][^.]{1,50})\s+refers?\s+to\s+(.+)$', re.IGNORECASE),
        re.compile(r'^Definition\s+of\s+([^:]+):\s*(.*)$', re.IGNORECASE),
    ]
    
    BULLET_PATTERN = re.compile(r'^[\s]*[•·▪▸▹►\-\*]\s+(.+)$')
    
    NUMBERED_LIST_PATTERN = re.compile(r'^[\s]*\d+[\).]\s+(.+)$')
    
    @staticmethod
    def identify_definition(line: str) -> Optional[Dict]:
        """Check if line is a definition and extract term"""
        for pattern in ContentTypeIdentifier.DEFINITION_PATTERNS:
            match = pattern.match(line.strip())
            if match:
                return {
                    'term': match.group(1).strip(),
                    'definition': match.group(2).strip() if len(match.groups()) > 1 else ''
                }
        return None
    
    @staticmethod
    def identify_content_type(lines: List[str]) -> str:
        """
        Identify the type of content in a block of lines
        
        Returns: 'definition' | 'bullet_block' | 'list' | 'paragraph'
        """
        
        if not lines:
            return 'paragraph'
        
        first_line = lines[0].strip()
        if ContentTypeIdentifier.identify_definition(first_line):
            return 'definition'
        
        bullet_count = 0
        list_count = 0
        
        for line in lines:
            if ContentTypeIdentifier.BULLET_PATTERN.match(line):
                bullet_count += 1
            elif ContentTypeIdentifier.NUMBERED_LIST_PATTERN.match(line):
                list_count += 1
        
        # If more than 50% are bullets, it's a bullet block
        if bullet_count > len(lines) * 0.5:
            return 'bullet_block'
        
        # If more than 50% are numbered, it's a list
        if list_count > len(lines) * 0.5:
            return 'list'
        
        return 'paragraph'


class StructuredDocumentBuilder:
    """Build structured document with true hierarchy from extraction result"""
    
    def __init__(self):
        self.heading_detector = HeadingDetector()
        self.content_identifier = ContentTypeIdentifier()
    
    def build(self, extraction_result: ExtractionResult) -> StructuredDocument:
        """
        Build structured document with nested hierarchy from extraction result
        
        Args:
            extraction_result: ExtractionResult from document extraction
        
        Returns:
            StructuredDocument with hierarchical structure
        """
        
        text = extraction_result.raw_text
        lines = text.split('\n')
        formatting_notes = extraction_result.formatting_notes
        
        chapters = []
        current_content_block = []
        current_block_start = 0
        blank_line_count = 0
        
        # Stack to maintain heading hierarchy
        # Each item: (level, node) where node is Chapter or Topic
        hierarchy_stack = []
        
        for line_num, line in enumerate(lines):
            # Get context lines for blank line detection
            prev_line = lines[line_num - 1] if line_num > 0 else ''
            next_line = lines[line_num + 1] if line_num < len(lines) - 1 else ''
            
            # Track consecutive blank lines
            if not line.strip():
                blank_line_count += 1
                # Only split content on 2+ consecutive blank lines
                if blank_line_count >= 2 and current_content_block and hierarchy_stack:
                    self._add_content_to_hierarchy(
                        hierarchy_stack,
                        current_content_block,
                        current_block_start,
                        line_num - blank_line_count
                    )
                    current_content_block = []
                continue
            
            blank_line_count = 0  # Reset on non-blank line
            
            # Check if this line is a heading
            heading_info = self.heading_detector.detect_heading(
                line, prev_line, next_line, formatting_notes
            )
            
            if heading_info:
                # Save accumulated content first
                if current_content_block and hierarchy_stack:
                    self._add_content_to_hierarchy(
                        hierarchy_stack,
                        current_content_block,
                        current_block_start,
                        line_num - 1
                    )
                    current_content_block = []
                
                # Handle hierarchy with stack
                level = heading_info['level']
                
                if level == 1:
                    # Top-level chapter
                    new_chapter = Chapter(
                        title=heading_info['title'],
                        level=1,
                        line_start=line_num
                    )
                    chapters.append(new_chapter)
                    # Reset stack with new chapter
                    hierarchy_stack = [(1, new_chapter)]
                else:
                    # Subsection - find correct parent
                    # Pop stack until we find a lower level (parent)
                    while hierarchy_stack and hierarchy_stack[-1][0] >= level:
                        hierarchy_stack.pop()
                    
                    # Create new section
                    new_section = Topic(
                        title=heading_info['title'],
                        level=level,
                        content='',
                        content_type='heading',
                        line_start=line_num,
                        line_end=line_num
                    )
                    
                    # Add to parent
                    if hierarchy_stack:
                        parent_level, parent_node = hierarchy_stack[-1]
                        if isinstance(parent_node, Chapter):
                            parent_node.sections.append(new_section)
                        elif isinstance(parent_node, Topic):
                            parent_node.subsections.append(new_section)
                    
                    # Push to stack
                    hierarchy_stack.append((level, new_section))
                
                current_block_start = line_num + 1
            else:
                # Accumulate content
                current_content_block.append(line)
        
        # Don't forget the last content block
        if current_content_block and hierarchy_stack:
            self._add_content_to_hierarchy(
                hierarchy_stack,
                current_content_block,
                current_block_start,
                len(lines) - 1
            )
        
        # Set end lines for chapters
        for chapter in chapters:
            if chapter.sections:
                chapter.line_end = self._get_last_line(chapter.sections[-1])
            else:
                chapter.line_end = chapter.line_start
        
        # Create metadata
        metadata = {
            'total_chapters': len(chapters),
            'file_type': extraction_result.file_type,
            'confidence_score': extraction_result.confidence_score,
            'warnings': extraction_result.warnings
        }
        
        return StructuredDocument(
            chapters=chapters,
            metadata=metadata
        )
    
    def _get_last_line(self, topic: Topic) -> int:
        """Recursively get the last line number of a topic and its subsections"""
        if topic.subsections:
            return self._get_last_line(topic.subsections[-1])
        return topic.line_end
    
    def _add_content_to_hierarchy(self, hierarchy_stack: List, content_lines: List[str],
                                   line_start: int, line_end: int):
        """Add content block to the appropriate level in hierarchy"""
        
        if not content_lines or not hierarchy_stack:
            return
        
        # Identify content type
        content_type = self.content_identifier.identify_content_type(content_lines)
        
        # Combine lines into content
        content = '\n'.join(content_lines)
        
        # Extract title
        title = ''
        if content_type == 'definition':
            def_info = self.content_identifier.identify_definition(content_lines[0])
            if def_info:
                title = def_info['term']
        elif len(content_lines[0]) < 100:
            title = content_lines[0][:50] + ('...' if len(content_lines[0]) > 50 else '')
        
        # Create content topic
        content_topic = Topic(
            title=title,
            level=hierarchy_stack[-1][0] + 1,
            content=content,
            content_type=content_type,
            line_start=line_start,
            line_end=line_end
        )
        
        # Add to current parent
        parent_level, parent_node = hierarchy_stack[-1]
        if isinstance(parent_node, Chapter):
            parent_node.sections.append(content_topic)
        elif isinstance(parent_node, Topic):
            parent_node.subsections.append(content_topic)
    
    def to_dict(self, structured_doc: StructuredDocument) -> Dict:
        """Convert StructuredDocument to dictionary format with nested structure"""
        
        def topic_to_dict(topic: Topic) -> Dict:
            """Convert Topic to dict recursively"""
            result = {
                'title': topic.title,
                'level': topic.level,
                'content': topic.content,
                'content_type': topic.content_type,
                'line_start': topic.line_start,
                'line_end': topic.line_end
            }
            if topic.subsections:
                result['subsections'] = [topic_to_dict(sub) for sub in topic.subsections]
            return result
        
        return {
            'chapters': [
                {
                    'title': chapter.title,
                    'level': chapter.level,
                    'sections': [topic_to_dict(section) for section in chapter.sections],
                    'line_start': chapter.line_start,
                    'line_end': chapter.line_end
                }
                for chapter in structured_doc.chapters
            ],
            'metadata': structured_doc.metadata
        }
