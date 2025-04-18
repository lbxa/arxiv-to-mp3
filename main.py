from pathlib import Path
import math
import concurrent.futures
import subprocess
import os
from itertools import repeat

from episode import (
    PDFTextSource,
    FileTextSource,
    TTSConverter,
    Uploader,
    parse_args,
)

BUCKET_NAME = os.getenv("BUCKET_NAME")
if not BUCKET_NAME:
    raise ValueError("Please set the BUCKET_NAME environment variable.")


def main():
    args = parse_args()

    if args.mode == "pdf":
        pdf_path = Path(__file__).parent / "papers" / args.pdf_file
        source = PDFTextSource(pdf_path, args.start_offset, args.end_offset)
        base_name = Path(args.pdf_file).stem
    else:
        text_path = Path(args.text_file)
        source = FileTextSource(text_path)
        base_name = Path(args.text_file).stem

    out_dir = Path(__file__).parent / "chunks" / base_name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {out_dir}")

    text = source.get_text_episode()
    if not text:
        print("No text found. Exiting.")
        return

    voice = getattr(args, "voice", None)
    converter = TTSConverter(voice)
    print(f"Using voice: {voice}")

    chunk_size = 4096
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
    Uploader(BUCKET_NAME).upload(merged, f"lib/{base_name}.mp3")


if __name__ == "__main__":
    main()
