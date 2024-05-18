import json
import os

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


# Define a custom exception for handling HTTP 429 Too Many Requests errors
class TooManyRequestsError(Exception):
    """Custom exception for handling HTTP 429 Too Many Requests errors."""

    pass


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
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


def extract_citations(response, sources):
    """
    Extracts sources that contributed to the response.

    Parameters:
    response (str): The response text.
    sources (list): A list of source objects.

    Returns:
    list: A list of citation objects containing 'id', 'context', and 'link'.
    """
    citations = []
    for source in sources:
        if source["context"] in response:
            # Create citation object if source context is in response
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
    data (list): A list of data objects containing responses and sources.

    Returns:
    list: A list of processed data objects with citations.
    """
    result = []
    # Extract the actual data list from the nested 'data' key
    for item in data["data"]:
        if not isinstance(item, dict):
            # Skip unexpected item formats
            print(f"Skipping unexpected item format: {item}")
            continue
        response = item.get("response", "")
        sources = item.get("source", [])
        citations = extract_citations(response, sources)
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


if __name__ == "__main__":
    page = 1
    while True:
        # Fetch data for the current page
        data = fetch_page(API_URL, page)
        if not data or "data" not in data:
            # Break the loop if no data is returned or 'data' key is missing
            break
        # Process the data to identify citations
        citations_result = process_data(data)
        # Save the processed data to a JSON file
        save_to_json(citations_result, page, OUTPUT_DIR)
        # Move to the next page
        page += 1

    # Print completion message
    print("All pages processed.")
