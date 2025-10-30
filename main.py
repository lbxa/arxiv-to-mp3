from pathlib import Path
import math
import concurrent.futures
import subprocess
import os
from itertools import repeat
from typing import Optional

from episode import (
    PDFTextSource,
    FileTextSource,
    TTSConverter,
    Uploader,
    parse_args,
)

BUCKET_NAME = os.getenv("BUCKET_NAME")


def generate_audio(
    mode: str,
    *,
    pdf_file: Optional[str] = None,
    start_offset: int = 0,
    end_offset: int = 0,
    text_file: Optional[str] = None,
    text_content: Optional[str] = None,
    voice: Optional[str] = None,
    provider: str = "openai",
    elevenlabs_voice_id: Optional[str] = None,
    chunk_size: int = 4096,
    base_name: Optional[str] = None,
    upload: bool = True,
) -> dict:
    if mode == "pdf":
        if not pdf_file:
            raise ValueError("pdf_file is required when mode is 'pdf'.")
        pdf_path = Path(pdf_file)
        if not pdf_path.is_absolute():
            pdf_path = Path(__file__).parent / "papers" / pdf_path
        source = PDFTextSource(pdf_path, start_offset, end_offset)
        text = source.get_text()
        if base_name is None:
            base_name = pdf_path.stem
    elif mode == "text":
        if text_content is not None:
            text = text_content
            if base_name is None and text_file:
                base_name = Path(text_file).stem
        else:
            if not text_file:
                raise ValueError(
                    "Provide text_file or text_content when mode is 'text'."
                )
            text_path = Path(text_file)
            if not text_path.is_absolute():
                text_path = Path(__file__).parent / text_path
            source = FileTextSource(text_path)
            text = source.get_text_episode()
            if base_name is None:
                base_name = text_path.stem
    else:
        raise ValueError("mode must be either 'pdf' or 'text'.")

    if not text:
        raise ValueError("No text available to convert to speech.")

    if base_name is None:
        base_name = "episode"

    out_dir = Path(__file__).parent / "chunks" / base_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {out_dir}")

    converter = TTSConverter(
        voice,
        provider=provider,
        elevenlabs_voice_id=elevenlabs_voice_id,
    )
    print(f"Using provider: {provider}, voice: {voice or converter.voice}")

    cost_per_char = 15e-6
    total_chars = len(text)
    num_chunks = math.ceil(total_chars / chunk_size)
    print(
        f"Chars: {total_chars}, Chunks: {num_chunks}, Cost: ${total_chars * cost_per_char:.4f}"
    )

    chunks = [
        (i, text[i * chunk_size : (i + 1) * chunk_size]) for i in range(num_chunks)
    ]
    workers = min(32, os.cpu_count() + 4)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        executor.map(converter.process_chunk, zip(repeat(out_dir), chunks))

    print("Finished chunk processing.")

    subprocess.run(
        f"yes | ./merge.sh {base_name}",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    merged = Path(__file__).parent / "lib" / f"{base_name}.mp3"

    uploaded_path = None
    if upload:
        if not BUCKET_NAME:
            raise ValueError(
                "Please set the BUCKET_NAME environment variable before uploading."
            )
        uploaded_path = f"lib/{base_name}.mp3"
        Uploader(BUCKET_NAME).upload(merged, uploaded_path)

    return {
        "chunks_directory": out_dir.as_posix(),
        "merged_file": merged.as_posix(),
        "uploaded_path": uploaded_path,
        "base_name": base_name,
    }


def main():
    args = parse_args()

    result = generate_audio(
        args.mode,
        pdf_file=getattr(args, "pdf_file", None),
        start_offset=getattr(args, "start_offset", 0),
        end_offset=getattr(args, "end_offset", 0),
        text_file=getattr(args, "text_file", None),
        voice=getattr(args, "voice", None),
        provider=getattr(args, "provider", "openai"),
        elevenlabs_voice_id=getattr(args, "elevenlabs_voice_id", None),
        chunk_size=getattr(args, "chunk_size", 4096),
        base_name=getattr(args, "base_name", None),
        upload=not getattr(args, "skip_upload", False),
    )

    print("Generation complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
