#!/usr/bin/env python3

from app.utils.text_processor import preprocess_farsi_text
import subprocess
import os

# Test content
test_content = """# عنوان تست

این یک متن **پررنگ** و *کج* است.

- آیتم اول
- آیتم دوم"""

print("=== ORIGINAL CONTENT ===")
print(repr(test_content))
print()

# Process the text
processed = preprocess_farsi_text(test_content)
print("=== PROCESSED CONTENT ===")
print(repr(processed))
print()

# Save to temporary file
with open('/tmp/test_processed.md', 'w', encoding='utf-8') as f:
    f.write(processed)

print("=== CONVERTING WITH PANDOC ===")

# Convert with Pandoc
cmd = [
    'pandoc',
    '/tmp/test_processed.md',
    '-o', '/tmp/test_output.docx',
    '--reference-doc=/app/outputs/reference_farsi.docx',
    '--metadata=lang:fa',
    '--metadata=dir:rtl',
    '--variable=mainfont:DejaVu Sans'
]

print("Command:", ' '.join(cmd))

try:
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    print("✅ Conversion successful")
    print(f"Output file size: {os.path.getsize('/tmp/test_output.docx')} bytes")

except subprocess.CalledProcessError as e:
    print(f"❌ Conversion failed: {e}")
    print(f"STDOUT: {e.stdout}")
    print(f"STDERR: {e.stderr}")
