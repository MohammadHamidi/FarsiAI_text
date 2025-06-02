import subprocess
import os
import logging
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import asyncio
import hashlib
import glob
import time

# Import configuration
from .config import OUT_DIR, ALLOWED, MAX_FILE_AGE_HOURS

# Setup enhanced logging
logger = logging.getLogger(__name__)

@dataclass
class ConversionStats:
    """Statistics for tracking conversion performance and usage."""
    input_size: int
    output_size: int
    conversion_time: float
    pandoc_version: str
    format: str
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

@dataclass
class FontConfig:
    """Configuration for Persian fonts and styling."""
    main_font: str = "Vazirmatn"
    fallback_fonts: List[str] = None
    heading_font: str = None
    mono_font: str = "Vazir Code"
    
    def __post_init__(self):
        if self.fallback_fonts is None:
            self.fallback_fonts = ["Sahel", "Estedad", "Tahoma", "Arial Unicode MS"]
        if self.heading_font is None:
            self.heading_font = self.main_font

class EnhancedConverter:
    """Enhanced document converter with comprehensive Persian support and robust error handling."""
    
    def __init__(self, font_config: Optional[FontConfig] = None):
        self.font_config = font_config or FontConfig()
        self.conversion_stats: List[ConversionStats] = []
        self._pandoc_version = None
        self._available_fonts = None
        self._temp_dirs = set()
        
        # Initialize and validate environment
        self._validate_environment()
        
    def _validate_environment(self) -> None:
        """Validate that all required tools and fonts are available."""
        try:
            # Check Pandoc installation
            result = subprocess.run(
                ["pandoc", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                self._pandoc_version = result.stdout.split('\n')[0]
                logger.info(f"Pandoc available: {self._pandoc_version}")
            else:
                raise RuntimeError("Pandoc not properly installed")
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.critical(f"Pandoc validation failed: {e}")
            raise RuntimeError("Pandoc is not available or not responding")
        
        # Validate output directory
        self._ensure_output_directory()
        
        # Check available fonts
        self._detect_available_fonts()
    
    def _ensure_output_directory(self) -> None:
        """Ensure output directory exists and is writable."""
        if not OUT_DIR:
            raise ValueError("OUT_DIR not configured")
            
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(OUT_DIR, f".test_{os.getpid()}")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            logger.info(f"Output directory validated: {OUT_DIR}")
            
        except Exception as e:
            logger.critical(f"Output directory validation failed: {e}")
            raise RuntimeError(f"Cannot use output directory '{OUT_DIR}': {e}")
    
    def _detect_available_fonts(self) -> None:
        """Detect available Persian fonts on the system."""
        try:
            # Try to get font list using fc-list
            result = subprocess.run(
                ["fc-list", ":", "family"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                fonts = set()
                for line in result.stdout.split('\n'):
                    if line.strip():
                        # Extract font family names
                        family = line.split(':')[0].strip()
                        fonts.add(family)
                
                self._available_fonts = fonts
                
                # Check if configured fonts are available
                main_available = self.font_config.main_font in fonts
                fallbacks_available = [f for f in self.font_config.fallback_fonts if f in fonts]
                
                logger.info(f"Font detection complete. Main font '{self.font_config.main_font}' available: {main_available}")
                logger.info(f"Available fallback fonts: {fallbacks_available}")
                
                if not main_available and not fallbacks_available:
                    logger.warning("No configured Persian fonts detected. Document styling may be suboptimal.")
            else:
                logger.warning("Could not detect system fonts using fc-list")
                self._available_fonts = set()
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Font detection failed - fc-list not available")
            self._available_fonts = set()
    
    def _get_best_font(self) -> str:
        """Get the best available font for the current system."""
        if not self._available_fonts:
            return self.font_config.main_font
            
        # Check main font first
        if self.font_config.main_font in self._available_fonts:
            return self.font_config.main_font
            
        # Check fallback fonts
        for font in self.font_config.fallback_fonts:
            if font in self._available_fonts:
                logger.info(f"Using fallback font: {font}")
                return font
                
        # If nothing found, use main font anyway
        logger.warning(f"No configured fonts available, using: {self.font_config.main_font}")
        return self.font_config.main_font
    
    def _create_temp_workspace(self) -> str:
        """Create a temporary workspace for conversion."""
        temp_dir = tempfile.mkdtemp(prefix="docright_")
        self._temp_dirs.add(temp_dir)
        return temp_dir
    
    def _cleanup_temp_workspace(self, temp_dir: str) -> None:
        """Clean up temporary workspace."""
        try:
            if temp_dir in self._temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)
                self._temp_dirs.discard(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    def _prepare_content(self, content: str) -> str:
        """Prepare and validate content for conversion."""
        if not content or not content.strip():
            raise ValueError("Content is empty or contains only whitespace")
        
        # Basic content validation
        content = content.strip()
        
        # Detect and log content characteristics
        char_count = len(content)
        word_count = len(content.split())
        has_persian = any('\u0600' <= char <= '\u06FF' for char in content)
        has_markdown = any(marker in content for marker in ['#', '*', '`', '|', '[', ']'])
        
        logger.info(f"Content analysis: {char_count} chars, {word_count} words, "
                   f"Persian: {has_persian}, Markdown: {has_markdown}")
        
        # Size limit check (50MB as text)
        if char_count > 50 * 1024 * 1024:
            raise ValueError(f"Content too large: {char_count} characters (max 50MB)")
        
        return content
    
    def _create_reference_docx(self, temp_dir: str) -> Optional[str]:
        """Create a custom reference DOCX with proper Persian styling."""
        try:
            reference_path = os.path.join(temp_dir, "reference.docx")
            
            # Create a minimal DOCX with Persian styles
            # This is a simplified approach - in production, you might want to use python-docx
            # to create a more sophisticated reference document
            
            basic_content = """# نمونه سند
            
متن نمونه برای تنظیم قالب‌بندی

## زیرعنوان

* فهرست اول
* فهرست دوم

**متن پررنگ** و *متن کج*

| ستون اول | ستون دوم |
|----------|----------|
| سلول ۱   | سلول ۲   |
"""
            
            # Create basic markdown file
            md_path = os.path.join(temp_dir, "reference.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(basic_content)
            
            # Convert to DOCX with our settings
            font = self._get_best_font()
            cmd = [
                "pandoc", md_path, "-o", reference_path,
                "--metadata=lang:fa",
                "--metadata=dir:rtl",
                f"--variable=mainfont:{font}",
                f"--variable=sansfont:{font}",
                f"--variable=monofont:{self.font_config.mono_font}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(reference_path):
                logger.info(f"Created reference DOCX: {reference_path}")
                return reference_path
            else:
                logger.warning(f"Failed to create reference DOCX: {result.stderr}")
                return None
                
        except Exception as e:
            logger.warning(f"Reference DOCX creation failed: {e}")
            return None
    
    def _build_pandoc_command(self, input_path: str, output_path: str, format: str, temp_dir: str) -> List[str]:
        """Build the Pandoc command with all necessary options."""
        if format not in ALLOWED:
            raise ValueError(f"Unsupported format: '{format}'. Allowed: {list(ALLOWED)}")
        
        cmd = ["pandoc", input_path, "-o", output_path]
        
        if format == "docx":
            font = self._get_best_font()
            
            # Basic RTL and language settings
            cmd.extend([
                "--metadata=lang:fa",
                "--metadata=dir:rtl",
                f"--variable=mainfont:{font}",
                f"--variable=sansfont:{font}",
                f"--variable=monofont:{self.font_config.mono_font}",
                "--variable=fontsize:12pt",
                "--variable=linestretch:1.5"
            ])
            
            # Try to use custom reference DOCX
            reference_path = self._create_reference_docx(temp_dir)
            if reference_path:
                cmd.append(f"--reference-doc={reference_path}")
            
            # Advanced options for better Persian support
            cmd.extend([
                "--wrap=preserve",
                "--columns=120",
                "--tab-stop=4"
            ])
            
        return cmd
    
    async def render_markdown_async(self, content: str, format: str) -> Tuple[str, ConversionStats]:
        """Asynchronously convert markdown content to specified format."""
        start_time = time.time()
        temp_dir = None
        
        try:
            # Prepare content
            content = self._prepare_content(content)
            input_size = len(content.encode('utf-8'))
            
            # Create temporary workspace
            temp_dir = self._create_temp_workspace()
            
            # Create input file
            input_path = os.path.join(temp_dir, "input.md")
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Create output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            output_filename = f"output_{timestamp}.{format}"
            output_path = os.path.join(OUT_DIR, output_filename)
            
            # Build command
            cmd = self._build_pandoc_command(input_path, output_path, format, temp_dir)
            
            logger.info(f"Executing conversion: {' '.join(cmd[:3])} ... (format: {format})")
            
            # Execute conversion
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=120.0)
            except asyncio.TimeoutError:
                result.terminate()
                await result.wait()
                raise subprocess.TimeoutExpired(cmd, 120)
            
            # Check result
            if result.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                logger.error(f"Pandoc failed (exit {result.returncode}): {error_msg}")
                raise subprocess.CalledProcessError(result.returncode, cmd, stderr=error_msg)
            
            # Validate output
            if not os.path.exists(output_path):
                raise RuntimeError(f"Output file not created: {output_path}")
            
            output_size = os.path.getsize(output_path)
            conversion_time = time.time() - start_time
            
            # Log success
            logger.info(f"Conversion successful: {input_size} -> {output_size} bytes in {conversion_time:.2f}s")
            
            # Create stats
            stats = ConversionStats(
                input_size=input_size,
                output_size=output_size,
                conversion_time=conversion_time,
                pandoc_version=self._pandoc_version or "unknown",
                format=format,
                timestamp=datetime.now(),
                success=True
            )
            
            self.conversion_stats.append(stats)
            
            return output_path, stats
            
        except Exception as e:
            conversion_time = time.time() - start_time
            error_msg = str(e)
            
            logger.error(f"Conversion failed after {conversion_time:.2f}s: {error_msg}")
            
            # Create error stats
            stats = ConversionStats(
                input_size=len(content.encode('utf-8')) if content else 0,
                output_size=0,
                conversion_time=conversion_time,
                pandoc_version=self._pandoc_version or "unknown",
                format=format,
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
            
            self.conversion_stats.append(stats)
            raise
            
        finally:
            # Cleanup temporary workspace
            if temp_dir:
                self._cleanup_temp_workspace(temp_dir)
    
    def render_markdown(self, content: str, format: str) -> Tuple[str, ConversionStats]:
        """Synchronous wrapper for markdown conversion."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.render_markdown_async(content, format))
    
    def get_conversion_statistics(self) -> Dict[str, Any]:
        """Get comprehensive conversion statistics."""
        if not self.conversion_stats:
            return {"message": "No conversions recorded"}
        
        successful = [s for s in self.conversion_stats if s.success]
        failed = [s for s in self.conversion_stats if not s.success]
        
        stats = {
            "total_conversions": len(self.conversion_stats),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.conversion_stats) * 100,
            "formats": {},
            "performance": {}
        }
        
        if successful:
            # Format breakdown
            for stat in successful:
                fmt = stat.format
                if fmt not in stats["formats"]:
                    stats["formats"][fmt] = {"count": 0, "total_size": 0, "avg_time": 0}
                stats["formats"][fmt]["count"] += 1
                stats["formats"][fmt]["total_size"] += stat.output_size
            
            # Performance metrics
            times = [s.conversion_time for s in successful]
            sizes = [s.input_size for s in successful]
            
            stats["performance"] = {
                "avg_conversion_time": sum(times) / len(times),
                "min_conversion_time": min(times),
                "max_conversion_time": max(times),
                "avg_input_size": sum(sizes) / len(sizes),
                "total_output_size": sum(s.output_size for s in successful)
            }
        
        if failed:
            # Common errors
            error_counts = {}
            for stat in failed:
                error = stat.error_message or "Unknown error"
                error_counts[error] = error_counts.get(error, 0) + 1
            
            stats["common_errors"] = sorted(
                error_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]  # Top 5 errors
        
        return stats
    
    def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> int:
        """Enhanced cleanup with better error handling and logging."""
        age_hours = max_age_hours or MAX_FILE_AGE_HOURS
        
        if not OUT_DIR or not os.path.isdir(OUT_DIR):
            logger.warning(f"Output directory '{OUT_DIR}' not available for cleanup")
            return 0
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=age_hours)
        except (TypeError, ValueError):
            logger.error(f"Invalid max_age_hours: '{age_hours}'. Must be a number.")
            return 0
        
        cleaned_count = 0
        cleaned_size = 0
        errors = []
        
        logger.info(f"Starting cleanup: removing files older than {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                for entry in os.scandir(OUT_DIR):
                    if entry.is_file():
                        future = executor.submit(self._cleanup_file, entry, cutoff_time)
                        futures.append(future)
                
                # Process results
                for future in futures:
                    try:
                        result = future.result(timeout=10)
                        if result:
                            cleaned_count += 1
                            cleaned_size += result
                    except Exception as e:
                        errors.append(str(e))
        
        except Exception as e:
            logger.error(f"Error during cleanup scan: {e}")
            return 0
        
        # Log results
        if cleaned_count > 0:
            size_mb = cleaned_size / (1024 * 1024)
            logger.info(f"Cleanup completed: removed {cleaned_count} files ({size_mb:.2f} MB)")
        else:
            logger.info("Cleanup completed: no old files found")
        
        if errors:
            logger.warning(f"Cleanup encountered {len(errors)} errors: {errors[:3]}...")
        
        return cleaned_count
    
    def _cleanup_file(self, entry: os.DirEntry, cutoff_time: datetime) -> Optional[int]:
        """Clean up a single file if it's older than cutoff time."""
        try:
            file_path = entry.path
            mod_time = datetime.fromtimestamp(entry.stat().st_mtime)
            
            if mod_time < cutoff_time:
                file_size = entry.stat().st_size
                os.remove(file_path)
                logger.debug(f"Removed: {file_path} ({file_size} bytes, modified: {mod_time})")
                return file_size
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to process file {entry.path}: {e}")
            return None
    
    def __del__(self):
        """Cleanup any remaining temporary directories."""
        for temp_dir in self._temp_dirs.copy():
            self._cleanup_temp_workspace(temp_dir)

# Global converter instance
_converter_instance = None

def get_converter() -> EnhancedConverter:
    """Get or create the global converter instance."""
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = EnhancedConverter()
    return _converter_instance

# Backward compatibility functions
def render_markdown(md_path: str, out_path: str, fmt: str) -> str:
    """Legacy function for backward compatibility."""
    logger.warning("Using legacy render_markdown function. Consider upgrading to EnhancedConverter.")
    
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        converter = get_converter()
        result_path, stats = converter.render_markdown(content, fmt)
        
        # Move result to expected location if different
        if result_path != out_path:
            shutil.move(result_path, out_path)
        
        return out_path
        
    except Exception as e:
        logger.error(f"Legacy conversion failed: {e}")
        raise

def cleanup_old_files() -> int:
    """Legacy cleanup function."""
    converter = get_converter()
    return converter.cleanup_old_files()

# Async convenience function
async def convert_text_async(content: str, format: str = "docx") -> Tuple[str, Dict[str, Any]]:
    """Asynchronously convert text content to specified format."""
    converter = get_converter()
    output_path, stats = await converter.render_markdown_async(content, format)
    return output_path, asdict(stats)