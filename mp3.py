from pathlib import Path
from openai import OpenAI
import math
import PyPDF2
import concurrent.futures
import os
from itertools import repeat

client = OpenAI()

def text_to_speech(text: str, speech_file_path: Path) -> None:
    """
    Converts text to speech and saves it to a specified file path.

    Args:
        text (str): The text to convert.
        speech_file_path (Path): The full path where the MP3 file will be saved.
    """
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
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

def process_chunk(filepath: Path, chunk_info: tuple) -> None:
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
    text_to_speech(chunk_text, speech_file_path)

def main():
    pdf_file = "attention.pdf"
    pdf_path = Path(__file__).parent / "papers" / pdf_file

    # Use pathlib to get the stem (filename without extension)
    folder_name = Path(pdf_file).stem
    filepath = Path(__file__).parent / "chunks" / folder_name
    filepath.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {filepath}")

    # Extract text with specified offsets. Some pages are either
    # blank or don't contain primary content e.g. table of contents
    # acknowledgments, references etc. 
    text = extract_text_from_pdf(pdf_path, offsets=(0, 5))

    if not text:
        print("No text extracted from the PDF. Exiting.")
        return

    cost_per_char = 15e-6  # $15.000 / 1M characters
    chunk_size = 4096
    n_chunks = math.ceil(len(text) / chunk_size)
    estimated_cost = len(text) * cost_per_char

    print(f"Total characters: {len(text)}")
    print(f"Number of chunks: {n_chunks}")
    print(f"ESTIMATED COST: ${estimated_cost:.4f}")

    chunks = []
    for chunk_index in range(n_chunks):
        start = chunk_size * chunk_index
        end = start + chunk_size
        chunk_text = text[start:end]
        chunks.append((chunk_index, chunk_text))

    # Determine the number of threads (adjust based on your system and API rate limits)
    max_workers = min(32, os.cpu_count() + 4)

    # Use ThreadPoolExecutor with itertools.repeat to pass the same filepath to all calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_chunk, repeat(filepath), chunks)

    print("All chunks have been processed.")

if __name__ == "__main__":
    main()
