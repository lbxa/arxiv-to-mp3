from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional

from main import generate_audio

app = FastAPI(title="arxiv-to-mp3 API")


class GenerateRequest(BaseModel):
    mode: Literal["pdf", "text"]
    pdf_file: Optional[str] = None
    start_offset: int = 0
    end_offset: int = 0
    text_file: Optional[str] = None
    text_content: Optional[str] = None
    voice: Optional[str] = None
    provider: Literal["openai", "elevenlabs"] = "openai"
    elevenlabs_voice_id: Optional[str] = None
    chunk_size: int = 4096
    base_name: Optional[str] = None
    upload: bool = True


class GenerateResponse(BaseModel):
    status: Literal["completed"]
    chunks_directory: str
    merged_file: str
    uploaded_path: Optional[str]
    base_name: str


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(request: GenerateRequest) -> GenerateResponse:
    try:
        result = generate_audio(
            request.mode,
            pdf_file=request.pdf_file,
            start_offset=request.start_offset,
            end_offset=request.end_offset,
            text_file=request.text_file,
            text_content=request.text_content,
            voice=request.voice,
            provider=request.provider,
            elevenlabs_voice_id=request.elevenlabs_voice_id,
            chunk_size=request.chunk_size,
            base_name=request.base_name,
            upload=request.upload,
        )
    except Exception as exc:  # pragma: no cover - runtime exception handling
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return GenerateResponse(status="completed", **result)
