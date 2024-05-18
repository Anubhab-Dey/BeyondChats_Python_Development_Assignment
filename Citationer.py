import json
import os
import time

import requests
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Load environment variables from a .env file
load_dotenv()

# Fetch the API URL and output directory from environment variables
API_URL = os.getenv(
    "API_URL", "https://devapi.beyondchats.com/api/get_message_with_sources"
)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "JSONs")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")
MAX_PAGE_LIMIT = 60


# Define a custom exception for handling HTTP 429 Too Many Requests errors
class TooManyRequestsError(Exception):
    """Custom exception for handling HTTP 429 Too Many Requests errors."""

    pass


@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=(
        retry_if_exception_type(requests.exceptions.RequestException)
        | retry_if_exception_type(TooManyRequestsError)
    ),
)
def fetch_page(api_url, page):
    """
    Fetches a single page of data from the API.

    Parameters:
    api_url (str): The URL of the API endpoint.
    page (int): The page number to fetch.

    Returns:
    dict: The JSON response from the API.

    Raises:
    TooManyRequestsError: If the API returns a 429 status code.
    """
    response = requests.get(api_url, params={"page": page})
    if response.status_code == 429:
        # Raise custom exception for Too Many Requests
        raise TooManyRequestsError(
            f"Too Many Requests: {response.status_code}"
        )
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    return data


def extract_citations(sources):
    """
    Extracts sources for the response.

    Parameters:
    sources (list): A list of source objects.

    Returns:
    list: A list of citation objects containing 'id', 'context', and 'link'.
    """
    citations = []
    for source in sources:
        citation = {
            "id": source["id"],
            "context": source["context"],
            "link": source.get("link", ""),
        }
        citations.append(citation)
    return citations


def process_data(data):
    """
    Processes the data to identify citations for each response.

    Parameters:
    data (dict): The data object containing responses and sources.

    Returns:
    list: A list of processed data objects with citations.
    """
    result = []
    # Extract the actual data list from the nested 'data' key
    items = data.get("data", {}).get("data", [])
    for item in items:
        if not isinstance(item, dict):
            # Skip unexpected item formats
            print(f"Skipping unexpected item format: {item}")
            continue
        response = item.get("response", "")
        sources = item.get("source", [])
        citations = extract_citations(sources)
        result.append({"response": response, "sources": citations})
    return result


def save_to_json(citations_result, page, directory):
    """
    Saves the citations result to a JSON file.

    Parameters:
    citations_result (list): A list of processed data objects with citations.
    page (int): The page number.
    directory (str): The directory to save the JSON files in.
    """
    # Ensure the output directory exists
    os.makedirs(directory, exist_ok=True)

    # Construct filename and filepath
    filename = f"Page_{page}.json"
    filepath = os.path.join(directory, filename)

    # Save the JSON data to the specified file
    with open(filepath, "w") as f:
        json.dump(citations_result, f, indent=4)

    # Print confirmation message
    print(f"Page {page} as JSON saved as '{filename}' at '{filepath}'")


def load_progress(progress_file):
    """
    Loads the last processed page from the progress file.

    Parameters:
    progress_file (str): The path to the progress file.

    Returns:
    int: The last processed page number.
    """
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            progress = json.load(f)
            return progress.get("last_page", 1)
    return 1


def save_progress(progress_file, last_page):
    """
    Saves the last processed page to the progress file.

    Parameters:
    progress_file (str): The path to the progress file.
    last_page (int): The last processed page number.
    """
    with open(progress_file, "w") as f:
        json.dump({"last_page": last_page}, f)


if __name__ == "__main__":
    last_processed_page = load_progress(PROGRESS_FILE)
    page = last_processed_page
    while page <= MAX_PAGE_LIMIT:
        try:
            # Fetch data for the current page
            data = fetch_page(API_URL, page)
            if not data or "data" not in data:
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
            time.sleep(2)
        except TooManyRequestsError as e:
            print(f"Error: {e}")
            # Wait longer before retrying after hitting rate limit
            time.sleep(13)

    # Delete the progress file if all pages are processed
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("Progress file deleted.")

    # Print completion message
    print("All pages processed.")
