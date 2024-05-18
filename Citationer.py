import json
import os

from dotenv import load_dotenv

from Methods import process_data, save_to_json

# Load environment variables from a .env file
load_dotenv()

# Fetch the output directory from environment variables
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "JSONs")


def process_and_save_all_files():
    """
    Processes and saves all JSON files in the OUTPUT_DIR.

    This function processes each JSON file in the OUTPUT_DIR to identify citations and matched sources.
    The processed data is then saved back to JSON files with a "Processed_" prefix.
    """
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith(".json") and filename.startswith("Page_"):
            page = filename.split("_")[1].split(".")[0]
            filepath = os.path.join(OUTPUT_DIR, filename)

            # Load the JSON data from the file
            with open(filepath, "r") as f:
                data = json.load(f)

            # Process the data to identify citations and matched sources
            citations_result = process_data(data)

            # Save the processed data back to a JSON file with a "Processed_" prefix
            save_to_json(citations_result, page, OUTPUT_DIR, processed=True)

            # Print confirmation message
            print(
                f"Processed Page {page} and saved as 'Processed_Page_{page}.json' in '{OUTPUT_DIR}'"
            )


def display_citations():
    """
    Displays the citations for each processed JSON file in the OUTPUT_DIR.

    This function reads each processed JSON file with a "Processed_" prefix from the OUTPUT_DIR,
    and prints the citations and matched sources in a user-friendly format.
    """
    for filename in os.listdir(OUTPUT_DIR):
        if filename.startswith("Processed_") and filename.endswith(".json"):
            filepath = os.path.join(OUTPUT_DIR, filename)

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


if __name__ == "__main__":
    # Process and save all files
    process_and_save_all_files()

    # Display the citations for each processed file
    display_citations()
