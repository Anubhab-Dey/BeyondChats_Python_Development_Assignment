import json
import os

import requests
import torch
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class TooManyRequestsError(Exception):
    """Custom exception for handling HTTP 429 Too Many Requests errors."""

    pass


def load_transformers_model(model_name="distilbert-base-uncased"):
    """
    Loads the transformers model.

    Parameters:
    model_name (str): The name of the transformers model to load.

    Returns:
    tuple: The tokenizer and model from transformers.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    return tokenizer, model


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


def save_to_json(data, page, directory, processed=False):
    """
    Saves the data to a JSON file.

    Parameters:
    data (dict): The data to be saved.
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
        json.dump(data, f, indent=4)

    # Print confirmation message
    print(f"Page {page} as JSON saved as '{filename}' at '{filepath}'")


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


def calculate_semantic_similarity(response, context, tokenizer, model):
    """
    Calculates the semantic similarity between the response and context using transformers.

    Parameters:
    response (str): The response text.
    context (str): The context text.
    tokenizer (transformers.AutoTokenizer): The tokenizer for the transformers model.
    model (transformers.AutoModelForSequenceClassification): The transformers model.

    Returns:
    float: The similarity score between the response and context.
    """
    inputs = tokenizer(
        response, context, return_tensors="pt", truncation=True, padding=True
    )
    outputs = model(**inputs)
    logits = outputs.logits
    probabilities = torch.nn.functional.softmax(logits, dim=-1)
    similarity_score = probabilities[0][1].item()

    return similarity_score


def match_sources(response, sources, tokenizer, model, threshold=0.75):
    """
    Matches sources with the response using semantic similarity.

    Parameters:
    response (str): The response text.
    sources (list): A list of source objects.
    tokenizer (transformers.AutoTokenizer): The tokenizer for the transformers model.
    model (transformers.AutoModelForSequenceClassification): The transformers model.
    threshold (float): The similarity threshold for matching.

    Returns:
    list: A list of matched sources.
    """
    matched_sources = []
    for source in sources:
        context = source["context"]
        similarity = calculate_semantic_similarity(
            response, context, tokenizer, model
        )
        if similarity >= threshold:
            matched_sources.append(source)
    return matched_sources


def process_data(data, tokenizer, model):
    """
    Processes the data to identify citations for each response.

    Parameters:
    data (dict): The data object containing responses and sources.
    tokenizer (transformers.AutoTokenizer): The tokenizer for the transformers model.
    model (transformers.AutoModelForSequenceClassification): The transformers model.

    Returns:
    list: A list of processed data objects with citations and matched sources.
    """
    result = []

    if isinstance(data, list):
        items = data
    else:
        items = data.get("data", {}).get("data", [])

    for item in items:
        if not isinstance(item, dict):
            # Skip unexpected item formats
            print(f"Skipping unexpected item format: {item}")
            continue
        response = item.get("response", "")
        sources = item.get("source", [])
        citations = extract_citations(sources)
        matched_sources = match_sources(response, sources, tokenizer, model)
        result.append(
            {
                "response": response,
                "sources": citations,
                "matched_sources": matched_sources,
            }
        )
    return result


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


def process_and_save_all_files(output_dir, tokenizer, model):
    """
    Processes and saves all JSON files in the specified output directory.

    Parameters:
    output_dir (str): The directory containing the JSON files to process.
    tokenizer (transformers.AutoTokenizer): The tokenizer for the transformers model.
    model (transformers.AutoModelForSequenceClassification): The transformers model.
    """
    for filename in os.listdir(output_dir):
        if filename.endswith(".json") and filename.startswith("Page_"):
            page = filename.split("_")[1].split(".")[0]
            filepath = os.path.join(output_dir, filename)

            # Load the JSON data from the file
            with open(filepath, "r") as f:
                data = json.load(f)

            # Process the data to identify citations and matched sources
            citations_result = process_data(data, tokenizer, model)

            # Save the processed data back to a JSON file with a "Processed_" prefix
            save_to_json(citations_result, page, output_dir, processed=True)

            # Print confirmation message
            print(
                f"Processed Page {page} and saved as 'Processed_Page_{page}.json' in '{output_dir}'"
            )


def display_citations(output_dir):
    """
    Displays the citations for each processed JSON file in the specified output directory.

    Parameters:
    output_dir (str): The directory containing the processed JSON files to display.
    """
    for filename in os.listdir(output_dir):
        if filename.startswith("Processed_") and filename.endswith(".json"):
            filepath = os.path.join(output_dir, filename)

            # Load the JSON data from the file
            with open(filepath, "r") as f:
                data = json.load(f)

            print(f"\nDisplaying citations for {filename}:")
            for item in data:
                print(f"\nResponse: {item['response']}")
                print("Citations:")
                for source in item["sources"]:
                    print(
                        f"  - {source['context']} (ID: {source['id']}, Link: {source['link']})"
                    )
                print("Matched Sources:")
                for source in item["matched_sources"]:
                    print(
                        f"  - {source['context']} (ID: {source['id']}, Link: {source['link']})"
                    )
