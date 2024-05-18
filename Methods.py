import json
import os
import re

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


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


def match_sources(response, sources):
    """
    Matches sources with the response.

    Parameters:
    response (str): The response text.
    sources (list): A list of source objects.

    Returns:
    list: A list of matched sources.
    """
    matched_sources = []
    for source in sources:
        context = source["context"]
        # Using regular expressions to find whole words and word boundaries
        if re.search(r"\b" + re.escape(context) + r"\b", response):
            matched_sources.append(source)
    return matched_sources


def process_data(data):
    """
    Processes the data to identify citations for each response.

    Parameters:
    data (dict): The data object containing responses and sources.

    Returns:
    list: A list of processed data objects with citations and matched sources.
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
        matched_sources = match_sources(response, sources)
        result.append(
            {
                "response": response,
                "sources": citations,
                "matched_sources": matched_sources,
            }
        )
    return result


def save_to_json(citations_result, page, directory, processed=False):
    """
    Saves the citations result to a JSON file.

    Parameters:
    citations_result (list): A list of processed data objects with citations.
    page (int): The page number.
    directory (str): The directory to save the JSON files in.
    processed (bool): Flag to indicate if the data is processed or raw.
    """
    # Ensure the output directory exists
    os.makedirs(directory, exist_ok=True)

    # Construct filename and filepath
    prefix = "Processed_" if processed else ""
    filename = f"{prefix}Page_{page}.json"
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
