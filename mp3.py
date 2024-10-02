from pathlib import Path
from typing import Literal
from openai import OpenAI
import math
import random
import PyPDF2
import concurrent.futures
import os
import sys
import subprocess
from itertools import repeat
from google.cloud import storage

BUCKET_NAME = "arxiv-audio-store"
type Voice = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

client = OpenAI()

def parse_args() -> list[str, int, int]:
    """
    Parses command line arguments.

    Returns:
        str: The path to the PDF file.
    """
    if len(sys.argv) != 4:
        print("Usage: python mp3.py <path_to_pdf> <start_offset> <end_offset>")
        sys.exit(1)
    return [sys.argv[1], int(sys.argv[2]), int(sys.argv[3])]


def text_to_speech(
    text: str, 
    speech_file_path: Path,
    voice: Voice = "alloy"
) -> None:
    """
    Converts text to speech and saves it to a specified file path.

    Args:
        text (str): The text to convert.
        speech_file_path (Path): The full path where the MP3 file will be saved.
    """   
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        response.stream_to_file(speech_file_path)
        print(f"Successfully created {speech_file_path.name}")
    except Exception as e:
        print(f"Error creating {speech_file_path.name}: {e}")

def extract_text_from_pdf(pdf_path: str, offsets=(0, 0)) -> str:
    """
    Extracts text from a PDF file, excluding specific pages.

    Args:
        pdf_path (str): Path to the PDF file.
        offsets (tuple): A tuple containing the number of pages to skip at the start and end.

    Returns:
        str: Extracted text.
    """
    extracted_text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            start, end = offsets
            for page_num in range(start, total_pages - end):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text
        print(f"Extracted text from {pdf_path}")
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
    return extracted_text

def process_chunk(filepath: Path, chunk_info: tuple, voice: Voice) -> None:
    """
    Processes a single text chunk by converting it to speech.

    Args:
        filepath (Path): The directory where the MP3 file will be saved.
        chunk_info (tuple): A tuple containing the chunk index and chunk text.
    """
    chunk_index, chunk_text = chunk_info
    filename = f"{chunk_index}.mp3"
    speech_file_path = filepath / filename
    print(f"Processing chunk {chunk_index}...")
    text_to_speech(chunk_text, speech_file_path, voice=voice)

def upload_to_storage(bucket_name: str, filepath: Path) -> None:
    """
    Uploads all MP3 files in the specified directory to a Google Cloud Storage bucket.

    Args:
        bucket_name (str): The name of the Google Cloud Storage bucket.
        filepath (Path): The directory containing the MP3 files to upload.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob = bucket.blob(filepath)
    try:
        blob.upload_from_filename(filepath)
        print(f"Uploaded {filepath} to {bucket_name}")
    except Exception as e:
        print(f"Error uploading {filepath}: {e}")

def main():
    pdf_file, offset_start, offset_end = parse_args()
    pdf_path = Path(__file__).parent / "papers" / pdf_file

    # Use pathlib to get the stem (filename without extension)
    folder_name = Path(pdf_file).stem
    filepath = Path(__file__).parent / "chunks" / folder_name
    filepath.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {filepath}")

    # Extract text with specified offsets. Some pages are either
    # blank or don't contain primary content e.g. table of contents
    # acknowledgments, references etc. 
    # text = extract_text_from_pdf(pdf_path, offsets=(offset_start, offset_end))

    # if not text:
    #     print("No text extracted from the PDF. Exiting.")
    #     return

    # # select speaker voice
    # voice: Voice = random.choice(["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

    # cost_per_char = 15e-6  # $15.000 / 1M characters
    # chunk_size = 4096
    # n_chunks = math.ceil(len(text) / chunk_size)
    # estimated_cost = len(text) * cost_per_char

    # print(f"Using voice: {voice}")
    # print(f"Total characters: {len(text)}")
    # print(f"Number of chunks: {n_chunks}")
    # print(f"ESTIMATED COST: ${estimated_cost:.4f}")

    # chunks = []
    # for chunk_index in range(n_chunks):
    #     start = chunk_size * chunk_index
    #     end = start + chunk_size
    #     chunk_text = text[start:end]
    #     chunks.append((chunk_index, chunk_text))

    # # Determine the number of threads (adjust based on your system and API rate limits)
    # max_workers = min(32, os.cpu_count() + 4)

    # # Use ThreadPoolExecutor with itertools.repeat to pass the same filepath to all calls
    # with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     executor.map(process_chunk, repeat(filepath), chunks, repeat(voice))

    # print("All chunks have been processed.")
    
    # merge all chunks into a single mp3 file
    # merge_cmd = ["./merge.sh", folder_name]
    # subprocess.run(merge_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    upload_to_storage(BUCKET_NAME, f"lib/{folder_name}.mp3")

if __name__ == "__main__":
    main()