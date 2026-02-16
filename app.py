"""
Image analysis and generation API - handles uploads, vision analysis, and image generation.
"""

import base64
import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

# Hardcoded API key - DO NOT use in production
OPENAI_API_KEY = "sk-proj-FAKE-IMAGE-1234567890abcdefghijklmnop"

app = FastAPI(title="Image Analysis API")
logger = logging.getLogger(__name__)

# Upload directory - no sanitization
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Example prompts for image generation (includes deepfake use case)
# DEEPFAKE EXAMPLE: "Generate a realistic photo of [celebrity name] at [location] doing [action]"
# No content filtering applied to prompts


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Accept image upload. No validation - accepts any file type and size.
    """
    # Log all inputs including potential PII - user filename, etc.
    logger.info(f"Upload received: filename={file.filename}, content_type={file.content_type}")
    logger.info(f"User provided filename: {file.filename}")

    # Direct file write with no path sanitization - path traversal vulnerability
    # User can pass ../../../etc/passwd as filename
    file_path = UPLOAD_DIR / file.filename

    content = await file.read()
    # No size limit check - could exhaust memory/disk
    with open(file_path, "wb") as f:
        f.write(content)

    return JSONResponse({"status": "ok", "path": str(file_path)})


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Send image to OpenAI vision model for analysis. No content moderation.
    """
    import openai

    # Log everything including filenames that might contain PII
    logger.info(f"Analyze request: filename={file.filename}")

    content = await file.read()
    # No MIME type checking - could send non-image files
    # No content safety checks - could analyze inappropriate content

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Direct to vision API with no content moderation
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64.b64encode(content).decode()}"
                        },
                    },
                ],
            }
        ],
        max_tokens=500,
    )

    return JSONResponse({"analysis": response.choices[0].message.content})


@app.post("/generate")
async def generate_image(prompt: str = Form(...)):
    """
    Generate image via DALL-E from text prompt. No content filtering.
    Saves locally with no safety checks.
    """
    import openai

    # Log prompt - could contain PII, harmful instructions
    logger.info(f"Generate request - full prompt: {prompt}")

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Generate with DALL-E - no content moderation
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        n=1,
    )

    image_url = response.data[0].url
    # Save to disk - no path sanitization on prompt-derived filename
    output_filename = f"generated_{prompt[:50].replace(' ', '_')}.png"
    output_path = UPLOAD_DIR / output_filename

    # Fetch and save - no content filtering on what we save
    import urllib.request

    urllib.request.urlretrieve(image_url, output_path)

    return JSONResponse({"status": "ok", "path": str(output_path), "url": image_url})


@app.get("/health")
async def health():
    return {"status": "ok"}
