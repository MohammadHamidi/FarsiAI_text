# DocRight

**DocRight** is a web-based application that converts Markdown text to properly formatted Word (DOCX) documents with comprehensive Right-to-Left (RTL) support, specifically optimized for Persian/Farsi content.

## Features

- **Advanced RTL Support**: Full right-to-left text direction with BiDi (bidirectional) properties
- **Persian Typography**: Automatic conversion of punctuation and quotes to Persian equivalents
- **Mixed Content Handling**: Proper handling of mixed RTL/LTR content (e.g., English text, URLs, code)
- **Enhanced Text Processing**: Unicode normalization, technical term preservation, and markdown enhancement
- **Multi-Stage Processing Pipeline**: Combines Pandoc conversion with custom XML post-processing for optimal results

## RTL Processing Pipeline

The application uses a sophisticated multi-stage pipeline to ensure proper RTL formatting:

### 1. **Text Preprocessing** (`app/utils/text_processor.py`)
   - Unicode normalization (NFKC)
   - Persian typography fixes:
     - Convert `,` → `،` (Persian comma)
     - Convert `;` → `؛` (Persian semicolon)
     - Convert `?` → `؟` (Persian question mark)
     - Convert `"text"` → `«text»` (Persian quotes)
   - Add YAML front matter with RTL metadata
   - Wrap LTR content (English, URLs, code) in appropriate direction tags
   - Preserve technical terms and code blocks

### 2. **Pandoc Conversion** (`app/converter.py`)
   - Convert Markdown to DOCX using Pandoc
   - Apply RTL configuration:
     - `--metadata=lang:fa` (Persian language)
     - `--metadata=dir:rtl` (Right-to-left direction)
     - `--variable=rtl:true` (RTL-specific options)
   - Use custom reference document with RTL styles:
     - RTL-aligned headings (H1-H6)
     - Right-aligned paragraphs
     - BiDi properties on all styles
     - Complex script support for Persian fonts

### 3. **XML Post-Processing** (`app/converter.py:apply_rtl_to_docx()`)
   **NEW**: This step ensures all paragraphs have the RTL BiDi property at the XML level:

   a. Opens the DOCX file (ZIP archive)
   b. Extracts `word/document.xml`
   c. Parses XML and finds all `<w:p>` (paragraph) elements
   d. For each paragraph:
      - Creates `<w:pPr>` (paragraph properties) if it doesn't exist
      - Adds `<w:bidi/>` element to ensure RTL direction
   e. Saves the modified XML back to the DOCX file

   This guarantees that **every paragraph** in the document has the RTL BiDi property set, regardless of Pandoc's default behavior.

### 4. **Result**
   - Properly formatted DOCX file with:
     - All paragraphs rendered right-to-left
     - Persian fonts (DejaVu Sans, Vazir, Sahel, Tanha)
     - Correct alignment and text direction
     - Mixed RTL/LTR content handled properly

## Run Locally with Docker

```bash
docker-compose up --build
```

Then visit http://localhost:8000

## Manual Setup (without Docker)

### Prerequisites
- Python 3.10+
- Pandoc
- Persian fonts (Vazir, Sahel, Tanha, DejaVu Sans)

### Installation

1. Install system dependencies:
```bash
# On Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y pandoc fonts-dejavu fonts-dejavu-core
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /` - Web interface
- `POST /api/convert` - Convert Markdown to DOCX
  - Request body: `{ "text": "markdown content", "format": "docx" }`
  - Returns: DOCX file as attachment
- `GET /health` - Health check
- `POST /api/admin/cleanup` - Manual cleanup (localhost only)

## Development

### Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── converter.py          # Pandoc conversion + RTL post-processing
│   ├── config.py             # Configuration
│   ├── firebase_utils.py     # Analytics
│   └── utils/
│       └── text_processor.py # Persian text preprocessing
├── static/
│   └── index.html           # Web interface
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker orchestration
└── requirements.txt         # Python dependencies
```

### Key Components

**converter.py** contains three main functions:
- `create_reference_docx()` - Creates RTL-configured reference document
- `render_markdown()` - Converts MD to DOCX using Pandoc
- `apply_rtl_to_docx()` - **NEW**: Post-processes DOCX to add BiDi properties

### Testing

Run the simple DOCX test:
```bash
python3 test_docx_simple.py
```

Run the RTL conversion test:
```bash
python3 test_rtl_conversion.py
```

## Technical Details

### Supported Formats
- Input: Markdown (with or without YAML front matter)
- Output: DOCX (Microsoft Word format)

### RTL BiDi Implementation

The application implements RTL support at multiple levels:

1. **Document Level**: Metadata (`lang: fa`, `dir: rtl`)
2. **Style Level**: Reference document with RTL styles
3. **Paragraph Level**: XML `<w:bidi/>` property on every paragraph

This multi-layered approach ensures maximum compatibility with Microsoft Word, LibreOffice, and other word processors.

### Font Support

The application includes comprehensive Persian font support:
- **DejaVu Sans**: Unicode support, complex scripts
- **Vazir**: Modern Persian font
- **Sahel**: Traditional Persian font
- **Tanha**: Decorative Persian font

### Rate Limiting

The API is rate-limited to 30 requests per minute per IP address.

### File Cleanup

Temporary files are automatically cleaned up after 24 hours.

## License

[Add your license here]

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pandoc](https://pandoc.org/)
- [python-docx](https://python-docx.readthedocs.io/)
- Persian fonts from [rastikerdar](https://github.com/rastikerdar)
