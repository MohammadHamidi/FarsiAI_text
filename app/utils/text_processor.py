"""
Enhanced text processing utilities for Farsi text formatting and typography improvements.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class FarsiTextProcessor:
    """
    Advanced text processor for Farsi text with typography and formatting enhancements.
    """

    def __init__(self):
        # Farsi punctuation and character mappings
        self.farsi_punctuations = {
            ',': '،',  # Comma
            ';': '؛',  # Semicolon
            '?': '؟',  # Question mark
            '%': '٪',  # Percent
        }

        # Common Farsi typography fixes
        self.typography_fixes = {
            # Fix spacing around punctuation
            r' +([،؛؟٪])': r'\1',  # Remove space before Farsi punctuation
            r'([،؛؟٪])(?!\s)': r'\1 ',  # Add space after Farsi punctuation
            # Fix multiple spaces
            r' +': ' ',
            # Fix line breaks and paragraphs
            r'\n\s*\n\s*\n+': '\n\n',  # Multiple empty lines to double
        }

    def preprocess_markdown(self, text: str) -> str:
        """
        Preprocess markdown text with Farsi-specific enhancements.

        Args:
            text: Input markdown text

        Returns:
            Enhanced markdown text
        """
        logger.info("Starting Farsi text preprocessing")

        # First, handle emoji and special characters
        text = self._handle_emojis_and_special_chars(text)

        # Apply typography fixes
        for pattern, replacement in self.typography_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)

        # Enhance headers with better Farsi formatting
        text = self._enhance_headers(text)

        # Improve list formatting for RTL
        text = self._enhance_lists(text)

        # Enhance code blocks with better RTL support
        text = self._enhance_code_blocks(text)

        # Improve table formatting for RTL
        text = self._enhance_tables(text)

        # Fix quotation marks
        text = self._fix_quotation_marks(text)

        # Handle mixed content (Farsi + English technical terms)
        text = self._handle_mixed_content(text)

        # Clean up excessive whitespace and formatting
        text = self._cleanup_formatting(text)

        logger.info("Farsi text preprocessing completed")
        return text

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
farsi_processor = FarsiTextProcessor()


def preprocess_farsi_text(text: str) -> str:
    """
    Main function to preprocess Farsi text with all enhancements.

    Args:
        text: Input text to process

    Returns:
        Processed text with enhancements
    """
    try:
        # Apply Farsi-specific preprocessing
        text = farsi_processor.preprocess_markdown(text)

        # Add advanced markdown features
        text = farsi_processor.add_markdown_features(text)

        return text
    except Exception as e:
        logger.error(f"Error in Farsi text preprocessing: {e}")
        return text  # Return original text if processing fails
