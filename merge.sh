#!/bin/bash

# ============================================
# Script: merge_mp3.sh
# Description: Merges multiple MP3 files from a specified directory into a single MP3 file using ffmpeg.
# Usage: ./merge_mp3.sh <name>
#        ./merge_mp3.sh -h | --help
# ============================================

# Function to display usage information
usage() {
    echo "Usage: $0 <name>"
    echo
    echo "Description:"
    echo "  Merges all MP3 files from the directory chunks/<name> into a single MP3 file lib/<name>.mp3."
    echo
    echo "Positional Arguments:"
    echo "  name        The name of the folder inside 'chunks' containing MP3 files to merge."
    echo
    echo "Options:"
    echo "  -h, --help  Display this help message and exit."
    echo
    echo "Example:"
    echo "  $0 attention"
    echo "  This will merge all MP3 files in chunks/attention/ into lib/attention.mp3"
}

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed. Please install ffmpeg to use this script."
    exit 1
fi

# Parse command-line arguments
if [[ $# -eq 0 ]]; then
    echo "Error: Missing required argument 'name'."
    usage
    exit 1
fi

# Handle help option
case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
    *)
        NAME="$1"
        ;;
esac

# Define variables based on the provided name
FOLDER_NAME="chunks/$NAME"
OUTPUT_DIR="lib"
OUTPUT_FILE="$OUTPUT_DIR/$NAME.mp3"
FILE_LIST="file_list.txt"

# Check if the specified directory exists
if [[ ! -d "$FOLDER_NAME" ]]; then
    echo "Error: Directory '$FOLDER_NAME' does not exist."
    exit 1
fi

# Create or empty the file_list.txt
> "$FILE_LIST"

# Populate file_list.txt with sorted MP3 file paths
mp3_files=("$FOLDER_NAME"/*.mp3)

# Check if there are any MP3 files in the directory
if [[ ${#mp3_files[@]} -eq 0 || ! -e "${mp3_files[0]}" ]]; then
    echo "Error: No MP3 files found in '$FOLDER_NAME'."
    exit 1
fi

# List and sort MP3 files numerically, then append to file_list.txt
ls "$FOLDER_NAME"/*.mp3 2>/dev/null | sort -V | while read -r file; do
    echo "file '$file'" >> "$FILE_LIST"
done

# Ensure the output directory exists
mkdir -p "$OUTPUT_DIR"

# Use ffmpeg to concatenate the MP3 files
ffmpeg -f concat -safe 0 -i "$FILE_LIST" -c copy "$OUTPUT_FILE"

# Check if ffmpeg succeeded
if [[ $? -eq 0 ]]; then
    echo "Successfully created '$OUTPUT_FILE'."
    # Clean up the temporary file list
    rm "$FILE_LIST"
else
    echo "Error: Failed to merge MP3 files."
    exit 1
fi
