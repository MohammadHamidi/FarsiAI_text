#!/usr/bin/env python3
"""
Simple test to verify DOCX generation with available fonts
"""

import os
import tempfile
from app.utils.text_processor import preprocess_farsi_text
from app.converter import render_markdown

def test_simple_docx():
    """Test simple DOCX generation"""

    # Simple test input
    test_input = """# تست فارسی

این یک متن **پررنگ** و *کج* است.

## لیست موارد

- مورد اول
- مورد دوم با Facebook API
- مورد سوم

> این یک نقل قول است.
"""

    print("=== SIMPLE DOCX TEST ===")
    print(f"Original text length: {len(test_input)} characters")

    # Process the text
    processed_text = preprocess_farsi_text(test_input)
    print(f"Processed text length: {len(processed_text)} characters")

    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False) as md_file:
        md_file.write(processed_text)
        md_path = md_file.name

    out_path = md_path.replace('.md', '.docx')

    try:
        # Convert to DOCX
        print("\nConverting to DOCX...")
        result_path = render_markdown(md_path, out_path, 'docx')

        # Check result
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ DOCX created: {result_path} ({file_size} bytes)")

            if file_size > 1000:
                print("✅ File size indicates proper DOCX generation")
                return True
            else:
                print("⚠️ File size seems small")
                return False
        else:
            print("❌ DOCX file not created")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    finally:
        # Cleanup
        try:
            if os.path.exists(md_path):
                os.unlink(md_path)
        except Exception as e:
            print(f"Warning: Could not cleanup: {e}")

if __name__ == "__main__":
    success = test_simple_docx()
    exit(0 if success else 1)
