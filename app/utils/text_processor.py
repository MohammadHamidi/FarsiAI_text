"""
Enhanced text processing utilities for Farsi text with improved RTL/LTR mixed content handling
"""

import re
import logging
import unicodedata
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class EnhancedFarsiTextProcessor:
    """
    Advanced text processor for Farsi text with proper RTL/LTR mixed content handling
    """

    def __init__(self):
        # Persian/Arabic character ranges
        self.persian_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        self.arabic_chars = r'[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06AF\u06BE\u06CC]'
        self.farsi_chars = r'[\u067E\u0686\u0698\u06AF\u06BE\u06CC\u0621-\u063A\u0641-\u064A]'

        # Latin character range
        self.latin_chars = r'[A-Za-z0-9]'

        # Common technical terms that should remain LTR
        self.ltr_terms = [
            r'\bAPI\b', r'\bGraph\b', r'\bInstagram\b', r'\bFacebook\b',
            r'\bn8n\b', r'\bAccess\s+Token\b', r'\bCredential\b', r'\bWorkflow\b',
            r'\bDashboard\b', r'\bMeta\b', r'\bBusiness\s+Account\b',
            r'\bProfessional\s+Account\b', r'\bAdmin\b', r'\bSettings\b',
            r'\bApp\s+ID\b', r'\bApp\s+Secret\b', r'\bOAuth\b', r'\bJSON\b',
            r'\bXML\b', r'\bHTML\b', r'\bCSS\b', r'\bJavaScript\b', r'\bPython\b',
            r'\bURL\b', r'\bHTTP\b', r'\bHTTPS\b', r'\bGitHub\b', r'\bGoogle\b',
            # Version numbers and codes
            r'\bv\d+\.\d+\b', r'\b\d+\.\d+\.\d+\b',
            # File extensions
            r'\.\w{2,4}\b',
            # Email patterns
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # URLs
            r'https?://[^\s<>"]+',
        ]

        # Persian punctuation mapping
        self.persian_punctuation = {
            ',': '،',
            ';': '؛',
            '?': '؟',
            '%': '٪',
        }

        # Typography fixes
        self.typography_rules = [
            # Fix spacing around Persian punctuation
            (r' +([،؛؟٪])', r'\1'),
            (r'([،؛؟٪])(?=[^\s])', r'\1 '),
            # Fix multiple spaces
            (r' +', ' '),
            # Fix Persian quotes
            (r'"([^"]*)"', r'«\1»'),
            (r"'([^']*)'", r'‹\1›'),
        ]

    def detect_language_spans(self, text: str) -> List[Tuple[str, str, int, int]]:
        """
        Detect language spans in mixed RTL/LTR text
        Returns list of (text_span, language, start_pos, end_pos)
        """
        spans = []
        current_lang = None
        current_start = 0

        i = 0
        while i < len(text):
            char = text[i]

            # Detect character type
            if re.match(self.farsi_chars, char):
                char_lang = 'fa'
            elif re.match(r'[A-Za-z0-9]', char):
                char_lang = 'en'
            else:
                # Neutral characters (spaces, punctuation) - inherit from context
                char_lang = current_lang

            # If language changes, save the previous span
            if char_lang != current_lang and current_lang is not None:
                span_text = text[current_start:i]
                if span_text.strip():  # Only add non-empty spans
                    spans.append((span_text, current_lang, current_start, i))
                current_start = i

            current_lang = char_lang
            i += 1

        # Add the final span
        if current_start < len(text):
            span_text = text[current_start:]
            if span_text.strip():
                spans.append((span_text, current_lang or 'fa', current_start, len(text)))

        return spans

    def wrap_ltr_content(self, text: str) -> str:
        """
        Wrap LTR content in appropriate markdown for proper rendering
        """
        # First, protect existing code blocks and inline code
        protected_blocks = []

        def protect_code(match):
            protected_blocks.append(match.group(0))
            return f"__PROTECTED_CODE_{len(protected_blocks)-1}__"

        # Protect code blocks and inline code
        text = re.sub(r'```[\s\S]*?```', protect_code, text)
        text = re.sub(r'`[^`\n]+`', protect_code, text)

        # Process LTR terms
        for term_pattern in self.ltr_terms:
            # Wrap technical terms in spans with LTR direction
            text = re.sub(
                term_pattern,
                lambda m: f'<span dir="ltr">{m.group(0)}</span>',
                text,
                flags=re.IGNORECASE
            )

        # Handle sequences of Latin characters mixed with Persian
        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            if not line.strip():
                processed_lines.append(line)
                continue

            # Skip if line is primarily code or already has direction markers
            if ('```' in line or line.strip().startswith('    ') or
                '<span dir=' in line or line.startswith('#')):
                processed_lines.append(line)
                continue

            # Detect and wrap LTR sequences
            spans = self.detect_language_spans(line)
            if len(spans) > 1:  # Mixed content
                result = ""
                for span_text, lang, start, end in spans:
                    if lang == 'en' and len(span_text.strip()) > 1:
                        # Wrap English spans
                        result += f'<span dir="ltr">{span_text}</span>'
                    else:
                        result += span_text
                processed_lines.append(result)
            else:
                processed_lines.append(line)

        text = '\n'.join(processed_lines)

        # Restore protected code blocks
        for i, block in enumerate(protected_blocks):
            text = text.replace(f"__PROTECTED_CODE_{i}__", block)

        return text

    def apply_persian_typography(self, text: str) -> str:
        """
        Apply Persian typography rules
        """
        # Convert common punctuation to Persian equivalents
        for latin, persian in self.persian_punctuation.items():
            text = text.replace(latin, persian)

        # Apply typography rules
        for pattern, replacement in self.typography_rules:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)

        return text

    def enhance_markdown_structure(self, text: str) -> str:
        """
        Enhance markdown structure for better RTL rendering
        """
        lines = text.split('\n')
        enhanced_lines = []

        in_code_block = False
        in_table = False

        for line in lines:
            original_line = line

            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                enhanced_lines.append(line)
                continue

            if in_code_block:
                enhanced_lines.append(line)
                continue

            # Detect tables
            if '|' in line and not line.strip().startswith('#'):
                in_table = True
                # Ensure proper table formatting
                if not line.strip().startswith('|'):
                    line = '| ' + line.strip()
                if not line.strip().endswith('|'):
                    line = line.rstrip() + ' |'
                # Clean up spacing
                line = re.sub(r'\s*\|\s*', ' | ', line)
                line = re.sub(r'^\s*\|\s*', '| ', line)
                line = re.sub(r'\s*\|\s*$', ' |', line)
            elif in_table and not line.strip():
                in_table = False

            # Enhance headers
            if line.startswith('#'):
                # Clean up header text
                header_match = re.match(r'^(#+)\s*(.*)$', line)
                if header_match:
                    level, title = header_match.groups()
                    title = title.strip()
                    if title:
                        line = f"{level} {title}"

            # Enhance lists
            if re.match(r'^\s*[-*+]\s', line):
                # Ensure consistent list formatting
                line = re.sub(r'^(\s*)([-*+])\s+', r'\1- ', line)
            elif re.match(r'^\s*\d+\.\s', line):
                # Clean up numbered lists
                line = re.sub(r'^(\s*)(\d+)\.\s+', r'\1\2. ', line)

            enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def add_rtl_metadata(self, text: str) -> str:
        """
        Add RTL metadata to markdown document
        """
        # Check if document already has YAML front matter
        if text.strip().startswith('---'):
            # Find end of front matter
            lines = text.split('\n')
            yaml_end = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    yaml_end = i
                    break

            if yaml_end > 0:
                # Insert RTL metadata into existing YAML
                yaml_section = lines[1:yaml_end]

                # Check if lang/dir already exist
                has_lang = any('lang:' in line for line in yaml_section)
                has_dir = any('dir:' in line for line in yaml_section)

                if not has_lang:
                    yaml_section.append('lang: fa')
                if not has_dir:
                    yaml_section.append('dir: rtl')

                # Reconstruct document
                result_lines = ['---'] + yaml_section + lines[yaml_end:]
                return '\n'.join(result_lines)

        # No front matter exists, add it
        yaml_header = """---
lang: fa
dir: rtl
---

"""
        return yaml_header + text

    def preprocess_text(self, text: str) -> str:
        """
        Main preprocessing function
        """
        logger.info("Starting enhanced Farsi text preprocessing")

        try:
            # Step 1: Normalize Unicode
            text = unicodedata.normalize('NFKC', text)

            # Step 2: Add RTL metadata
            text = self.add_rtl_metadata(text)

            # Step 3: Apply Persian typography
            text = self.apply_persian_typography(text)

            # Step 4: Enhance markdown structure
            text = self.enhance_markdown_structure(text)

            # Step 5: Handle mixed LTR/RTL content
            text = self.wrap_ltr_content(text)

            # Step 6: Final cleanup
            text = self.final_cleanup(text)

            logger.info("Enhanced Farsi text preprocessing completed")
            return text

        except Exception as e:
            logger.error(f"Error in text preprocessing: {e}")
            return text  # Return original text on error

    def final_cleanup(self, text: str) -> str:
        """
        Final cleanup and normalization
        """
        # Remove excessive empty lines
        text = re.sub(r'\n\s*\n\s*\n\s*\n+', '\n\n', text)

        # Clean up spaces around punctuation
        text = re.sub(r'\s+([،؛؟٪!])', r'\1', text)
        text = re.sub(r'([،؛؟٪!])(?=[^\s])', r'\1 ', text)

        # Fix spacing around parentheses
        text = re.sub(r'\s*\(\s*', ' (', text)
        text = re.sub(r'\s*\)\s*', ') ', text)

        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)

        return text.strip()

    def _enhance_headers(self, text: str) -> str:
        """Enhance markdown headers with better Farsi formatting."""
        lines = text.split('\n')
        enhanced_lines = []

        for line in lines:
            # Enhance ATX headers (# ## ###)
            if line.startswith('#'):
                # Count the number of # symbols
                header_level = len(line.split()[0]) if line.split() else 0
                if 1 <= header_level <= 6:
                    header_text = line[header_level:].strip()
                    if header_text:
                        # Clean up header text - remove extra spaces and normalize
                        header_text = re.sub(r'\s+', ' ', header_text).strip()

                        # Handle headers with anchor links like {#anchor}
                        anchor_match = re.search(r'\{#([^}]+)\}', header_text)
                        if anchor_match:
                            anchor = anchor_match.group(1)
                            header_text = re.sub(r'\s*\{#[^}]+\}', '', header_text)
                            enhanced_lines.append(f"{'#' * header_level} {header_text} {{#{anchor}}}")
                        else:
                            enhanced_lines.append(f"{'#' * header_level} {header_text}")
                    else:
                        enhanced_lines.append(line)
                else:
                    enhanced_lines.append(line)
            elif re.match(r'^=+$', line.strip()):
                # Handle Setext headers (underlined with =)
                if enhanced_lines and not enhanced_lines[-1].startswith('#'):
                    # Convert to ATX header
                    prev_line = enhanced_lines[-1]
                    enhanced_lines[-1] = f"# {prev_line}"
                    continue  # Skip adding the underline
                enhanced_lines.append(line)
            elif re.match(r'^-+$', line.strip()):
                # Handle Setext headers (underlined with -)
                if enhanced_lines and not enhanced_lines[-1].startswith('#'):
                    # Convert to ATX header
                    prev_line = enhanced_lines[-1]
                    enhanced_lines[-1] = f"## {prev_line}"
                    continue  # Skip adding the underline
                enhanced_lines.append(line)
            else:
                enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _enhance_lists(self, text: str) -> str:
        """Enhance list formatting for better RTL display."""
        lines = text.split('\n')
        enhanced_lines = []
        in_list = False
        list_type = None

        for line in lines:
            stripped = line.strip()

            # Handle unordered lists
            if re.match(r'^\s*[-*+]\s', line):
                # Ensure proper spacing after list markers
                line = re.sub(r'^(\s*)([-*+])\s*', r'\1\2 ', line)
                in_list = True
                list_type = 'unordered'

            # Handle ordered lists
            elif re.match(r'^\s*\d+\.\s', line):
                # Ensure proper spacing after numbers
                line = re.sub(r'^(\s*)(\d+)\.\s*', r'\1\2. ', line)
                in_list = True
                list_type = 'ordered'

            # Handle continuation lines in lists
            elif in_list and stripped and not stripped.startswith('#') and not re.match(r'^\s*[-*+]\s', line) and not re.match(r'^\s*\d+\.\s', line):
                # This is a continuation of a list item
                if list_type == 'unordered':
                    # Add consistent indentation for unordered list continuation
                    line = re.sub(r'^\s*', '  ', line)
                elif list_type == 'ordered':
                    # Add consistent indentation for ordered list continuation
                    line = re.sub(r'^\s*', '   ', line)

            # Reset list state for empty lines or headers
            elif not stripped or stripped.startswith('#'):
                in_list = False
                list_type = None

            enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _enhance_code_blocks(self, text: str) -> str:
        """Enhance code blocks with better RTL support."""
        # For inline code, ensure proper spacing
        text = re.sub(r'`([^`\n]+)`', r' `\1` ', text)

        # For code blocks, preserve LTR direction for code
        lines = text.split('\n')
        in_code_block = False
        enhanced_lines = []

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                enhanced_lines.append(line)
            elif in_code_block:
                # Keep code blocks as LTR
                enhanced_lines.append(line)
            else:
                enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _enhance_tables(self, text: str) -> str:
        """Enhance table formatting for RTL display."""
        lines = text.split('\n')
        enhanced_lines = []
        in_table = False

        for line in lines:
            # Detect table rows (lines with | separators)
            if '|' in line and not line.strip().startswith('|'):
                # Add leading and trailing | for proper table formatting
                if not line.strip().startswith('|'):
                    line = '| ' + line.strip()
                if not line.strip().endswith('|'):
                    line = line.rstrip() + ' |'

                # Ensure proper spacing around |
                line = re.sub(r'\s*\|\s*', ' | ', line)
                line = re.sub(r'^\s*\|\s*', '| ', line)
                line = re.sub(r'\s*\|\s*$', ' |', line)

            enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _fix_quotation_marks(self, text: str) -> str:
        """Fix quotation marks for proper Farsi typography."""
        # Replace straight quotes with proper quotation marks
        text = re.sub(r'"([^"]*)"', r'«\1»', text)  # Double quotes to Persian quotes
        text = re.sub(r"'([^']*)'", r'‹\1›', text)  # Single quotes to Persian quotes

        return text

    def add_markdown_features(self, text: str) -> str:
        """
        Add enhanced markdown features for better formatting.

        Args:
            text: Input text

        Returns:
            Text with enhanced markdown features
        """
        # Add table of contents generation
        if '<!-- TOC -->' in text:
            text = self._generate_toc(text)

        # Add footnote support
        text = self._process_footnotes(text)

        # Add definition lists support
        text = self._process_definition_lists(text)

        return text

    def _generate_toc(self, text: str) -> str:
        """Generate table of contents from headers."""
        lines = text.split('\n')
        toc_lines = []
        toc_marker_found = False

        for i, line in enumerate(lines):
            if '<!-- TOC -->' in line:
                toc_marker_found = True
                toc_lines.append(line)
                continue

            if toc_marker_found and line.startswith('#'):
                header_level = len(line.split()[0]) if line.split() else 0
                if 1 <= header_level <= 3:  # Only include h1-h3 in TOC
                    header_text = line[header_level:].strip()
                    indent = '  ' * (header_level - 1)
                    # Create anchor link
                    anchor = re.sub(r'[^\w\s-]', '', header_text.lower())
                    anchor = re.sub(r'[\s]+', '-', anchor)
                    toc_lines.append(f"{indent}- [{header_text}](#{anchor})")

        # Replace the TOC marker with actual TOC
        if toc_marker_found:
            toc_content = '\n'.join(toc_lines)
            text = text.replace('<!-- TOC -->', toc_content)

        return text

    def _process_footnotes(self, text: str) -> str:
        """Process footnote syntax [^1] into proper markdown footnotes."""
        # This is a basic implementation - can be enhanced further
        footnote_pattern = r'\[\^(\d+)\]'
        footnotes = []

        def footnote_replacer(match):
            footnote_num = match.group(1)
            return f'[^{footnote_num}]'

        text = re.sub(footnote_pattern, footnote_replacer, text)
        return text

    def _process_definition_lists(self, text: str) -> str:
        """Process definition list syntax."""
        # Convert term: definition format to proper markdown
        lines = text.split('\n')
        enhanced_lines = []

        for line in lines:
            # Look for term: definition pattern
            if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    term, definition = parts
                    enhanced_lines.append(f"**{term.strip()}**")
                    enhanced_lines.append(f": {definition.strip()}")
                else:
                    enhanced_lines.append(line)
            else:
                enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _handle_emojis_and_special_chars(self, text: str) -> str:
        """Handle emojis and special characters properly."""
        # Preserve emojis and special characters
        # Remove excessive emoji usage
        text = re.sub(r'([🚀✅⚠️📋🎯💡🎉🔧📊📄])(\1+)', r'\1', text)

        # Ensure proper spacing around emojis
        text = re.sub(r'([^\s])([🚀✅⚠️📋🎯💡🎉🔧📊📄])', r'\1 \2', text)
        text = re.sub(r'([🚀✅⚠️📋🎯💡🎉🔧📊📄])([^\s])', r'\1 \2', text)

        return text

    def _handle_mixed_content(self, text: str) -> str:
        """Handle mixed Farsi and English content properly."""
        lines = text.split('\n')
        enhanced_lines = []

        for line in lines:
            # Preserve technical terms and proper nouns
            # Keep English technical terms as-is
            technical_terms = [
                r'\bAPI\b', r'\bGraph\b', r'\bInstagram\b', r'\bFacebook\b',
                r'\bn8n\b', r'\bAccess Token\b', r'\bCredential\b', r'\bWorkflow\b',
                r'\bDashboard\b', r'\bMeta\b', r'\bBusiness Account\b',
                r'\bProfessional Account\b', r'\bAdmin\b', r'\bSettings\b'
            ]

            # Ensure proper spacing around technical terms
            for term in technical_terms:
                line = re.sub(f'({term})', r' `\1` ', line, flags=re.IGNORECASE)

            # Clean up excessive backticks
            line = re.sub(r'`\s*`\s*`\s*`+', r'`', line)
            line = re.sub(r'`\s+([^`]+?)\s+`', r'`\1`', line)

            enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _cleanup_formatting(self, text: str) -> str:
        """Clean up excessive whitespace and formatting issues."""
        # Remove excessive empty lines
        text = re.sub(r'\n\s*\n\s*\n\s*\n+', '\n\n', text)

        # Fix inconsistent indentation
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()

            # Normalize list indentation
            if re.match(r'^\s*[-*+]\s', line):
                line = re.sub(r'^\s+', '', line)  # Remove excessive indentation
                line = '- ' + line[2:] if line.startswith('- ') else line
            elif re.match(r'^\s*\d+\.\s', line):
                line = re.sub(r'^\s+', '', line)  # Remove excessive indentation

            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # Final cleanup
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        return text.strip()


# Global processor instance
enhanced_processor = EnhancedFarsiTextProcessor()


def preprocess_farsi_text(text: str) -> str:
    """
    Enhanced preprocessing function for Farsi text with proper RTL/LTR mixed content handling

    Args:
        text: Input text to process

    Returns:
        Processed text with enhancements for DOCX generation
    """
    return enhanced_processor.preprocess_text(text)
