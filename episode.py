import random
from pathlib import Path
from typing import Literal
import argparse
import os
import PyPDF2
from openai import OpenAI
from google.cloud import storage

Voice = Literal[
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]

DEFAULT_VOICES = [
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]


class TextSource:
    def get_text(self) -> str:
        raise NotImplementedError


class PDFTextSource(TextSource):
    def __init__(self, pdf_path: Path, start_offset: int, end_offset: int):
        self.pdf_path = pdf_path
        self.start_offset = start_offset
        self.end_offset = end_offset

    def get_text(self) -> str:
        extracted_text = ""
        try:
            with open(self.pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                for i in range(self.start_offset, total_pages - self.end_offset):
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        extracted_text += page_text
            print(f"Extracted text from {self.pdf_path}")
        except Exception as e:
            print(f"Error extracting from {self.pdf_path}: {e}")
        return extracted_text


class FileTextSource(TextSource):
    def __init__(self, text_file_path: Path, api_client: OpenAI = None):
        self.text_file_path = text_file_path

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable.")
        self.api_client = api_client or OpenAI()

    def get_text(self) -> str:
        try:
            text = self.text_file_path.read_text(encoding="utf-8")
            print(f"Read text from {self.text_file_path}")
            return text
        except Exception as e:
            print(f"Error reading {self.text_file_path}: {e}")
            return ""

    def get_text_episode(self) -> str:
        system_prompt = """
        You are an AI assistant that turns academic research papers (provided in full Markdown with equations) into engaging, digestible podcast scripts. Follow these rules:

            1. Structure  
            - **Intro**: Hook the listener with the big picture—why this paper matters.  
            - **Body**:  
                a) **Problem** – What’s the challenge?  
                b) **Approach** – How did they tackle it?  
                c) **Key Equations** – For each:  
                    1. Assign a symbolic anchor (e.g. “Lᵢ”) rather than reading the full formula.  
                    2. Define each symbol (“Lᵢ is the loss on adaptation data for task i”).  
                    3. Decompose the equation into primitive operations (“there’s an outer sum over each example d…”).  
                    4. Explain in plain language how those parts fit (“we sum the token‑level language‑model losses for each datapoint, then add the test‑token loss”).  
                d) **Results** – What did they find?  
            - **Conclusion**: Summarize takeaways and future directions.

            2. Tone & Depth  
            - **Dual Focus**: Blend consumer‑friendly clarity with rigorous technical depth.  
            - Use analogies **sparingly**—only when they illuminate without obscuring nuance.  
            - Keep jargon precise; don’t shy from technical terms when they’re key.

            3. Scope  
            - **Include**: Core ideas and their supporting equations (explained via symbolic anchors).  
            - **Ignore**: References, bibliographies, and appendices.
            - **Link**: Link other related papers and resources if they're relevant to the paper.

            4. Output  
            - A ready‑to‑record podcast script in plain text 
            - [IMPORTANT] Do not use any Markdown formatting, headers, bullets, bold, italics or citation blocks — plain spoken‑style prose only.
        """

        with open(self.text_file_path, "r", encoding="utf-8") as f:
            text = f.read()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        response = self.api_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=30000,
        )

        return response.choices[0].message.content


class TTSConverter:
    def __init__(self, voice: Voice = None, api_client: OpenAI = None):
        self.voice = voice or random.choice(DEFAULT_VOICES)
        self.client = api_client or OpenAI()

    def text_to_speech(self, text: str, out_path: Path) -> None:
        try:
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice=self.voice,
                input=text,
                instructions="Speak in a conversational tone, like a podcast.",
            ) as response:
                response.stream_to_file(out_path)
                print(f"Created {out_path.name}")
        except Exception as e:
            print(f"Error creating {out_path.name}: {e}")

    def process_chunk(self, args):
        out_dir, chunk_info = args
        idx, text = chunk_info
        file_path = out_dir / f"{idx}.mp3"
        print(f"Processing chunk {idx}")
        self.text_to_speech(text, file_path)


class Uploader:
    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload(self, local_path: Path, remote_path: str) -> None:
        blob = self.bucket.blob(remote_path)
        try:
            blob.upload_from_filename(local_path.as_posix())
            print(f"Uploaded {remote_path}")
        except Exception as e:
            print(f"Error uploading {remote_path}: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert PDF or text to MP3")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    pdf_parser = subparsers.add_parser("pdf", help="PDF mining mode")
    pdf_parser.add_argument("pdf_file", help="PDF filename in papers/")
    pdf_parser.add_argument("start_offset", type=int, help="Pages to skip at start")
    pdf_parser.add_argument("end_offset", type=int, help="Pages to skip at end")

    text_parser = subparsers.add_parser("text", help="Direct text mode")
    text_parser.add_argument("text_file", help="Path to text file")
    text_parser.add_argument("--voice", choices=DEFAULT_VOICES, help="Voice to use")

    return parser.parse_args()
