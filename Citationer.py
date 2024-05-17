import os

import requests
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Fetch the API URL from environment variables
API_URL = os.getenv(
    "API_URL", "https://devapi.beyondchats.com/api/get_message_with_sources"
)


def fetch_data_from_api(api_url):
    """
    Fetches data from the paginated API endpoint.

    Args:
        api_url (str): The API URL to fetch data from.

    Returns:
        list: A list of data objects retrieved from the API.
    """
    data = []
    page = 1
    while True:
        response = requests.get(api_url, params={"page": page})
        if response.status_code != 200:
            print(
                f"Failed to fetch data from API. Status code: {response.status_code}"
            )
            break
        page_data = response.json()
        if not page_data:
            break
        data.extend(page_data)
        page += 1
    return data


def identify_sources(response, sources):
    """
    Identifies sources for a given response text.

    Args:
        response (str): The response text to check against sources.
        sources (list): A list of source objects to check.

    Returns:
        list: A list of citation objects that match the response text.
    """
    citations = []
    for source in sources:
        if source["context"] in response:
            citation = {"id": source["id"], "link": source.get("link", "")}
            citations.append(citation)
    return citations


def process_data(data):
    """
    Processes data objects to identify citations.

    Args:
        data (list): A list of data objects from the API.

    Returns:
        list: A list of processed data objects with citations.
    """
    result = []
    for item in data:
        response = item.get("response", "")
        sources = item.get("sources", [])
        citations = identify_sources(response, sources)
        result.append({"response": response, "citations": citations})
    return result


def print_results(results):
    """
    Prints the results in an attractive, descriptive format.

    Args:
        results (list): A list of processed data objects with citations.
    """
    for i, item in enumerate(results, start=1):
        print(f"\n--- Response {i} ---")
        print(f"Response:\n{item['response']}\n")
        if item["citations"]:
            print("Citations:")
            for citation in item["citations"]:
                link = (
                    citation["link"]
                    if citation["link"]
                    else "No link available"
                )
                print(f"- ID: {citation['id']}, Link: {link}")
        else:
            print("Citations: None")
        print("\n" + "-" * 50)


if __name__ == "__main__":
    # Fetch data from the API
    data = fetch_data_from_api(API_URL)
    # Process the data to find citations
    citations_result = process_data(data)
    # Print the results
    print_results(citations_result)
