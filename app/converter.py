import subprocess
import os
import logging
from datetime import datetime, timedelta
import glob
# Ensure these are correctly imported from your config module
# and that the config module itself is correctly set up.
from .config import OUT_DIR, ALLOWED, MAX_FILE_AGE_HOURS

# Setup logging
logger = logging.getLogger(__name__)

def render_markdown(md_path: str, out_path: str, fmt: str):
    """
    Convert Markdown to the specified format using Pandoc.
    Currently focused on DOCX with RTL text justification and custom main font.

    Args:
        md_path: Path to source markdown file
        out_path: Path where output should be saved
        fmt: Output format (should be "docx" based on current ALLOWED config)

    Raises:
        ValueError: If format is not supported based on ALLOWED formats.
        subprocess.CalledProcessError: If Pandoc returns a non-zero exit code.
        subprocess.TimeoutExpired: If Pandoc command times out.
        FileNotFoundError: If Pandoc executable is not found.
        Exception: For other unexpected OS or subprocess errors during conversion.
    """
    if fmt not in ALLOWED:
        logger.error(f"Unsupported format requested: '{fmt}'. Allowed formats are: {ALLOWED}")
        raise ValueError(f"Unsupported format: '{fmt}'. Only formats in {list(ALLOWED)} are supported.")

    logger.info(f"Attempting to convert '{md_path}' to '{fmt}', outputting to '{out_path}'")

    cmd = ["pandoc", md_path, "-o", out_path]

    if fmt == "docx":
        # Enhanced Farsi font configuration
        custom_farsi_font_name = "Arial"  # Using Arial as primary font for better compatibility

        # Basic RTL and language settings
        cmd += [
            "--metadata=lang:fa",
            "--metadata=dir:rtl",
            f"--variable=mainfont:{custom_farsi_font_name}",
            "--variable=fontsize:12pt",
            "--variable=geometry:margin=1in",  # Standard margins
            "--variable=linestretch:1.5",  # Better line spacing
            "--variable=colorlinks=true",
            "--variable=linkcolor=blue",
            "--variable=urlcolor=blue",
        ]

        # Use reference document for consistent styling
        reference_docx_path = "/app/outputs/reference.docx"
        if os.path.exists(reference_docx_path):
            cmd += [f"--reference-doc={reference_docx_path}"]
            logger.info(f"Using custom reference DOCX: '{reference_docx_path}'")
        else:
            logger.warning(f"Custom reference DOCX '{reference_docx_path}' not found. Creating one...")
            # Create a basic reference document if it doesn't exist
            try:
                from docx import Document
                from docx.shared import Pt
                from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

                doc = Document()
                styles = doc.styles

                # Configure Normal style
                normal_style = styles['Normal']
                normal_font = normal_style.font
                normal_font.name = custom_farsi_font_name
                normal_font.size = Pt(12)
                normal_style.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

                # Configure Heading 1
                h1_style = styles['Heading 1']
                h1_font = h1_style.font
                h1_font.name = custom_farsi_font_name
                h1_font.size = Pt(18)
                h1_font.bold = True
                h1_style.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

                doc.save(reference_docx_path)
                cmd += [f"--reference-doc={reference_docx_path}"]
                logger.info(f"Created and using new reference DOCX: '{reference_docx_path}'")
            except Exception as e:
                logger.error(f"Failed to create reference DOCX: {e}")

        # Advanced formatting options
        cmd += [
            "--variable=documentclass:article",
            "--variable=classoption:twoside",  # For professional documents
            "--variable=indent:true",  # Paragraph indentation
            "--variable=subscript:true",  # Enable subscript
            "--variable=superscript:true",  # Enable superscript
            "--variable=strikeout:true",  # Enable strikeout
            "--variable=underline:true",  # Enable underline
        ]

        logger.info(f"Enhanced DOCX configuration with RTL support, reference document, and advanced formatting.")

    logger.debug(f"Executing Pandoc command: \"{' '.join(cmd)}\"")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            timeout=60,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if result.stdout and result.stdout.strip():
            logger.debug(f"Pandoc STDOUT:\n{result.stdout.strip()}")
        if result.stderr and result.stderr.strip():
            logger.warning(f"Pandoc STDERR (may contain warnings/info):\n{result.stderr.strip()}")
        logger.info(f"Successfully converted '{md_path}' to '{out_path}'")
        return out_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc command failed with exit code {e.returncode} during conversion of '{md_path}' to '{fmt}'.")
        logger.error(f"Pandoc command executed: \"{' '.join(e.cmd)}\"")
        logger.error(f"Pandoc STDOUT (on error): {e.stdout.strip() if e.stdout and e.stdout.strip() else '<empty>'}")
        logger.error(f"Pandoc STDERR (on error): {e.stderr.strip() if e.stderr and e.stderr.strip() else '<empty>'}")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except OSError as re: logger.warning(f"Failed to remove '{out_path}' after error: {re}")
        raise
    except subprocess.TimeoutExpired as e:
        logger.error(f"Pandoc command timed out after {e.timeout}s for '{md_path}' to '{fmt}'. Cmd: \"{' '.join(e.cmd)}\"")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except OSError as re: logger.warning(f"Failed to remove '{out_path}' after timeout: {re}")
        raise
    except FileNotFoundError:
        logger.critical(f"Pandoc executable ('{cmd[0]}') not found. Ensure Pandoc is installed and in PATH.")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during conversion of '{md_path}' to '{fmt}': {e}", exc_info=True)
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except OSError as re: logger.warning(f"Failed to remove '{out_path}' after error: {re}")
        raise

def cleanup_old_files():
    """
    Remove temporary files older than MAX_FILE_AGE_HOURS from OUT_DIR.
    """
    if not OUT_DIR or not os.path.isdir(OUT_DIR):
        logger.warning(f"Output directory '{OUT_DIR}' is not configured or does not exist. Skipping cleanup.")
        return 0
    try:
        cutoff_time = datetime.now() - timedelta(hours=MAX_FILE_AGE_HOURS)
    except TypeError:
        logger.error(f"Invalid MAX_FILE_AGE_HOURS: '{MAX_FILE_AGE_HOURS}'. Must be a number. Skipping cleanup.")
        return 0
    count = 0
    logger.info(f"Starting cleanup of files older than {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} in '{OUT_DIR}'")
    try:
        for entry in os.scandir(OUT_DIR):
            if entry.is_file():
                try:
                    file_path = entry.path
                    mod_time_timestamp = entry.stat().st_mtime
                    mod_time = datetime.fromtimestamp(mod_time_timestamp)
                    if mod_time < cutoff_time:
                        os.remove(file_path)
                        count += 1
                        logger.debug(f"Removed old file: '{file_path}' (modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
                except OSError as e:
                    logger.warning(f"Failed to process or remove old file '{entry.path}': {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error processing file '{entry.path}' for cleanup: {e}")
    except OSError as e:
        logger.error(f"Error scanning output directory '{OUT_DIR}' for cleanup: {e}")
        return 0
    if count > 0:
        logger.info(f"Cleaned up {count} old file(s) from '{OUT_DIR}'.")
    else:
        logger.info(f"No old files found to clean up in '{OUT_DIR}'.")
    return count