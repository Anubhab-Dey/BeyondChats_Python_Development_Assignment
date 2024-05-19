import os

from dotenv import load_dotenv

from Methods import (
    display_citations,
    load_transformers_model,
    process_and_save_all_files,
)

# Load environment variables from a .env file
load_dotenv()

# Fetch the output directory from environment variables
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "JSONs")

# Load the transformers model
tokenizer, model = load_transformers_model()

if __name__ == "__main__":
    # Process and save all files
    process_and_save_all_files(OUTPUT_DIR, tokenizer, model)

    # Display the citations for each processed file
    display_citations(OUTPUT_DIR)
