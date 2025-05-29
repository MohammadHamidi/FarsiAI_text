from fastapi import FastAPI, Form, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import http_exception_handler
import uuid
import os
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Callable # Keep Callable if used

from .converter import render_markdown, cleanup_old_files
from .config import settings, OUT_DIR # settings.ALLOWED_FORMATS will be {"docx"}
from .firebase_utils import initialize_firebase, track_event # Add Firebase imports

# Setup logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DocRight API",
    description="Convert Markdown text to DOCX with RTL support", # MODIFIED description
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter implementation
class RateLimiter:
    def __init__(self, limit: int = settings.RATE_LIMIT):
        self.limit = limit
        self.requests: Dict[str, list] = {}

    def is_rate_limited(self, ip: str) -> bool:
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        if ip not in self.requests:
            self.requests[ip] = []
        else:
            self.requests[ip] = [ts for ts in self.requests[ip] if ts > minute_ago]

        if len(self.requests[ip]) >= self.limit:
            return True

        self.requests[ip].append(now)
        return False

rate_limiter = RateLimiter()

async def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if rate_limiter.is_rate_limited(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

def schedule_cleanup():
    try:
        count = cleanup_old_files()
        logger.info(f"Scheduled cleanup removed {count} files")
    except Exception as e:
        logger.error(f"Error during scheduled cleanup: {e}")

@app.get("/", response_class=HTMLResponse)
async def homepage():
    try:
        # Ensure path is correct relative to this file's location
        html_file_path = Path(__file__).parent.parent / "static" / "index.html"
        with open(html_file_path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception as e:
        logger.error(f"Error serving homepage: {e}", exc_info=True)
        raise HTTPException(500, "Unable to serve homepage")

BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    logger.error(f"Static directory not found at: {STATIC_DIR}")
    # Decide how to handle this - raise an error or proceed?
    # For now, we'll let it fail at mount if it's truly missing.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/api/admin/cleanup") # Keep if you want admin cleanup
async def admin_cleanup(request: Request):
    if request.client and request.client.host not in ("127.0.0.1", "localhost"):
        raise HTTPException(403, "Forbidden")
    count = cleanup_old_files()
    return {"status": "success", "files_removed": count}

@app.post("/api/convert", dependencies=[Depends(check_rate_limit)])
async def convert(
    background_tasks: BackgroundTasks,
    request: Request,
    text: str = Form(...),
    format: str = Form(...) # format will now always be "docx" based on frontend
):
    if format not in settings.ALLOWED_FORMATS:
        # This check is still good, though frontend should only send "docx"
        raise HTTPException(400, f"Format must be 'docx'. Received: {format}")

    if len(text.encode('utf-8')) > settings.MAX_INPUT_SIZE:
        raise HTTPException(413, "Input text too large")

    # Track conversion event
    if settings.FIREBASE_ANALYTICS_ENABLED:
        user_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        await track_event(
            "conversion_requested", 
            {"format": format, "text_length": len(text)},
            user_ip=user_ip,
            user_agent=user_agent
        )

    uid = uuid.uuid4().hex
    md_file = os.path.join(OUT_DIR, f"{uid}.md")
    # Format will be 'docx'
    out_file = os.path.join(OUT_DIR, f"{uid}.{format}")

    logger.info(f"Converting to {format}, text length: {len(text)} chars, UID: {uid}")

    try:
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        logger.error(f"Failed to write markdown file {md_file}: {e}", exc_info=True)
        raise HTTPException(500, "Failed to process your request (writing md)")

    try:
        start_time = time.time()
        render_markdown(md_file, out_file, format)
        duration = time.time() - start_time
        logger.info(f"Conversion to {format} completed in {duration:.2f} seconds for {out_file}")

        background_tasks.add_task(schedule_cleanup)

        return FileResponse(
            out_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", # Only DOCX
            filename=f"farsi_text.{format}" # format will be "docx"
        )
    except ValueError as e: # From render_markdown if format is somehow wrong
        logger.warning(f"Format validation error during conversion: {e}")
        raise HTTPException(400, str(e))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # These are already logged in detail by render_markdown
        logger.error(f"Pandoc execution failed for {md_file} to {format}: {type(e).__name__}")
        raise HTTPException(500, "Conversion failed due to an internal processing error.")
    except Exception as e:
        logger.error(f"Unexpected error during conversion process for {md_file} to {format}: {e}", exc_info=True)
        # Clean up files, as render_markdown might not have caught this specific top-level error
        for f_path in (md_file, out_file):
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except OSError:
                    logger.warning(f"Could not clean up {f_path} after error.")
        raise HTTPException(500, "An unexpected error occurred during conversion.")
    # No finally here for cleanup, as render_markdown and specific exceptions handle it.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc} for request {request.method} {request.url}", exc_info=True)
    # Avoid re-raising HTTPException if it's already one, let FastAPI handle it
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    return await http_exception_handler(
        request,
        HTTPException(500, "An unexpected internal error occurred.")
    )

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting DocRight with output dir: {OUT_DIR}")
    # Output directory creation is now handled by Pydantic settings validator
    # os.makedirs(OUT_DIR, exist_ok=True) # Still good to have, or rely on validator
    initialize_firebase() # Initialize Firebase
    cleanup_old_files()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down DocRight")
    # Gracefully close the httpx client
    from .firebase_utils import client as httpx_client # Get the client instance
    await httpx_client.aclose()