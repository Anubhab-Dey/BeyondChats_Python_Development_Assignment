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

# Fetch the API URL from environment variables
API_URL = os.getenv(
    "API_URL", "https://devapi.beyondchats.com/api/get_message_with_sources"
)


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
        raise TooManyRequestsError(
            f"Too Many Requests: {response.status_code}"
        )
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()


def identify_sources(response, sources):
    """
    Identifies sources that contributed to the response.

    Parameters:
    response (str): The response text.
    sources (list): A list of source objects.

    Returns:
    list: A list of citation objects containing 'id' and 'link'.
    """
    citations = []
    for source in sources:
        if source["context"] in response:
            citation = {"id": source["id"], "link": source.get("link", "")}
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
    for item in data:
        if not isinstance(item, dict):
            print(f"Skipping unexpected item format: {item}")
            continue
        response = item.get("response", "")
        sources = item.get("sources", [])
        citations = identify_sources(response, sources)
        result.append({"response": response, "citations": citations})
    return result


def save_to_json(citations_result, page, directory="JSONs"):
    """
    Saves the citations result to a JSON file.

    Parameters:
    citations_result (list): A list of processed data objects with citations.
    page (int): The page number.
    directory (str): The directory to save the JSON files in.
    """
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)

    filename = f"Page_{page}.json"
    filepath = os.path.join(directory, filename)
    with open(filepath, "w") as f:
        json.dump(citations_result, f, indent=4)
    print(f"Page {page} as JSON saved as '{filename}' at '{filepath}'")


if __name__ == "__main__":
    page = 1
    while True:
        data = fetch_page(API_URL, page)
        if not data:
            break
        citations_result = process_data(data)
        save_to_json(citations_result, page)
        page += 1

    print("All pages processed.")
