import json
import os

from dotenv import load_dotenv

from Methods import process_data, save_to_json

# Load environment variables from a .env file
load_dotenv()

# Fetch the output directory from environment variables
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "JSONs")

if __name__ == "__main__":
    # Process each JSON file in the OUTPUT_DIR
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

    # Print completion message
    print("All files processed.")
