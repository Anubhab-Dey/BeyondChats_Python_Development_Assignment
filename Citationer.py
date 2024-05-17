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
    Fetches data from the paginated API.

    Parameters:
    api_url (str): The URL of the API endpoint.

    Returns:
    list: A list of data objects retrieved from the API.
    """
    data = []
    page = 1
    while True:
        try:
            response = requests.get(api_url, params={"page": page})
            response.raise_for_status()  # Raise an exception for HTTP errors
            page_data = response.json()
            if not page_data:
                break
            data.extend(page_data)
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch data from API. Error: {e}")
            break
    return data


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
        response = item.get("response", "")
        sources = item.get("sources", [])
        citations = identify_sources(response, sources)
        result.append({"response": response, "citations": citations})
    return result


def print_citations(citations_result):
    """
    Prints the citations in a formatted manner.

    Parameters:
    citations_result (list): A list of processed data objects with citations.
    """
    for item in citations_result:
        print("=" * 80)
        print(f"Response:\n{item['response']}\n")
        if item["citations"]:
            print("Citations:")
            for citation in item["citations"]:
                print(f"  - ID: {citation['id']}")
                if citation["link"]:
                    print(f"    Link: {citation['link']}")
        else:
            print("Citations: None")
        print("=" * 80)
        print()


if __name__ == "__main__":
    data = fetch_data_from_api(API_URL)
    if data:
        citations_result = process_data(data)
        print_citations(citations_result)
    else:
        print("No data was fetched from the API.")
