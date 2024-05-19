import json
import os

from dotenv import load_dotenv

from Methods import (
    TooManyRequestsError,
    fetch_page,
    load_progress,
    save_progress,
    save_to_json,
)

# Load environment variables from a .env file
load_dotenv()

# Fetch the API URL and output directory from environment variables
API_URL = os.getenv("API_URL")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "JSONs")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")

if __name__ == "__main__":
    # Load the last page from progress or start from 1
    last_page = load_progress(PROGRESS_FILE)

    # Fetch and save data until no more pages are left
    while True:
        try:
            data = fetch_page(API_URL, last_page)
            if not data:
                break
            save_to_json(data, last_page, OUTPUT_DIR)
            save_progress(PROGRESS_FILE, last_page)
            last_page += 1
        except TooManyRequestsError:
            print("Too many requests error. Exiting.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    # Delete the progress file if no more pages are left
    if last_page > 13:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            print(f"Deleted progress file: {PROGRESS_FILE}")
