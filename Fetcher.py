import os
import time

from dotenv import load_dotenv

from Methods import (
    TooManyRequestsError,
    fetch_page,
    load_progress,
    process_data,
    save_progress,
    save_to_json,
)

# Load environment variables from a .env file
load_dotenv()

# Fetch the API URL and output directory from environment variables
API_URL = os.getenv(
    "API_URL", "https://devapi.beyondchats.com/api/get_message_with_sources"
)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "JSONs")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")

if __name__ == "__main__":
    last_processed_page = load_progress(PROGRESS_FILE)
    page = last_processed_page
    while True:
        try:
            # Fetch data for the current page
            data = fetch_page(API_URL, page)
            if not data or "data" not in data or not data["data"]["data"]:
                # Break the loop if no data is returned or 'data' key is missing
                break
            # Process the data to identify citations
            citations_result = process_data(data)
            # Save the processed data to a JSON file
            save_to_json(citations_result, page, OUTPUT_DIR)
            # Save the progress
            save_progress(PROGRESS_FILE, page)
            # Move to the next page
            page += 1
            # Sleep to avoid hitting the rate limit too quickly
            time.sleep(1)
        except TooManyRequestsError as e:
            print(f"Error: {e}")
            # Wait longer before retrying after hitting rate limit
            time.sleep(60)

    # Delete the progress file if all pages are processed
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("Progress file deleted.")

    # Print completion message
    print("All pages processed.")
