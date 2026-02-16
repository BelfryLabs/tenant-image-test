"""
Image analysis and generation API - handles uploads, vision analysis, and image generation.
WARNING: This code contains intentional vulnerabilities for security testing.
"""

import base64
import logging
import os
from pathlib import Path

import openai
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# VULNERABILITY: Hardcoded API key fallback - scanner should detect this.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or "sk-proj-FAKE1234567890abcdefghijklmnopqrstuvwxyz"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Image Analysis API")
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# DEEPFAKE PROMPT EXAMPLE (for scanner detection):
# "Generate a photorealistic image of [celebrity name] at [location] doing [action]"
# No content moderation is applied to prompts - harmful requests are not filtered.


class AnalyzeRequest(BaseModel):
    image_url: str


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """
    VULNERABILITY: Accepts any file - no type validation, no size limit.
    VULNERABILITY: No path sanitization - filename used directly (path traversal possible).
    """
    # Log everything - potential PII leak
    logger.info(f"Upload: filename={file.filename}, content_type={file.content_type}")

    # UNSANITIZED: file.filename used directly - ../../../etc/passwd possible
    file_path = UPLOAD_DIR / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return JSONResponse({"status": "ok", "path": str(file_path)})


@app.post("/analyze")
async def analyze_image(req: Request):
    """
    VULNERABILITY: No content moderation on input image or output.
    VULNERABILITY: Logs everything including URLs (may contain PII).
    Accepts either {"image_url": str} in JSON or file upload.
    """
    content_type = req.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await req.json()
        image_url = body.get("image_url", "")
        image_content = [
            {"type": "text", "text": "Describe this image in detail."},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
        logger.info(f"Analyze request - image_url={image_url}")
    elif "multipart/form-data" in content_type:
        form = await req.form()
        file = form.get("file")
        if not file or not hasattr(file, "read"):
            return JSONResponse({"error": "No file provided"}, status_code=400)
        content = await file.read()
        b64 = base64.b64encode(content).decode()
        image_content = [
            {"type": "text", "text": "Describe this image in detail."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]
        logger.info(f"Analyze request - filename={getattr(file, 'filename', 'unknown')}")
    else:
        return JSONResponse({"error": "Provide JSON with image_url or multipart file"}, status_code=400)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": image_content}],
        max_tokens=500,
    )

    # No output filtering - raw analysis returned
    return JSONResponse({"analysis": response.choices[0].message.content})


@app.post("/generate")
async def generate_image(request: GenerateRequest):
    """
    VULNERABILITY: No content filtering on prompt - harmful requests not blocked.
    VULNERABILITY: UNSANITIZED filename - prompt used directly in path (injection possible).
    """
    logger.info(f"Generate request - prompt: {request.prompt}")

    response = client.images.generate(
        model="dall-e-3",
        prompt=request.prompt,
        size="1024x1024",
        n=1,
    )

    image_url = response.data[0].url
    # UNSANITIZED: prompt used in filename - path traversal, special chars, etc.
    output_filename = f"generated_{request.prompt[:80].replace(' ', '_')}.png"
    output_path = UPLOAD_DIR / output_filename

    import urllib.request
    urllib.request.urlretrieve(image_url, str(output_path))

    return JSONResponse({"status": "ok", "path": str(output_path), "url": image_url})


@app.get("/health")
async def health():
    return {"status": "ok"}
