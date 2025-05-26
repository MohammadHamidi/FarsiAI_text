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
        # --- REPLACE 'Vazirmatn' with the actual system name of your chosen Farsi font ---
        # You can find this name by running `fc-list | grep -i YourFontPartialName` inside the Docker container
        # after you've installed the font via the Dockerfile.
        custom_farsi_font_name = "Vazirmatn" # Example: "Vazirmatn", "Sahel", "Estedad", or your custom font's system name

        cmd += [
            "--metadata=lang:fa",  # Sets the document language to Farsi
            "--metadata=dir:rtl",  # Sets the base text direction to Right-to-Left
            f"--variable=mainfont:{custom_farsi_font_name}" # Tells Pandoc to use this as the main body font
            # Optionally, if your font has distinct styles for sans-serif or mono and you want to enforce them:
            # f"--variable=sansfont:{custom_farsi_font_name}",
            # f"--variable=monofont:{custom_farsi_font_name}",
        ]
        logger.info(f"Added RTL metadata and mainfont='{custom_farsi_font_name}' for DOCX.")

        # --- Optional: Using a reference.docx for more style control (e.g., bold color, specific heading fonts) ---
        # If you also want to control specific style attributes like bold color, heading fonts/sizes/colors,
        # or paragraph spacing in more detail, you would use a reference.docx.
        # The --variable=mainfont sets the base font, but a reference.docx defines the "Normal", "Heading 1",
        # "Strong" (for bold) styles, etc.
        #
        # 1. Create 'reference.docx' with your desired styles (e.g., "Normal" style using your custom_farsi_font_name,
        #    "Strong" style with a specific color if desired).
        # 2. Copy 'reference.docx' into your Docker image (e.g., to '/app/reference.docx').
        # 3. Uncomment the following lines:
        #
        # reference_docx_path = "/app/reference.docx"
        # if os.path.exists(reference_docx_path):
        #     cmd += [f"--reference-doc={reference_docx_path}"]
        #     logger.info(f"Using custom reference DOCX: '{reference_docx_path}'")
        # else:
        #     logger.warning(f"Custom reference DOCX '{reference_docx_path}' not found. "
        #                    "Relying on mainfont variable, metadata, and Pandoc's default styling for DOCX.")
        # --- End Optional ---

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