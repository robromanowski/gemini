import argparse
from collections import Counter
import sys

def count_items_in_file(input_filepath):
    """
    Reads a file line by line and counts the occurrences of each unique line (item).

    Args:
        input_filepath (str): Path to the input text file.
    """
    item_counts = Counter() # Use Counter for efficient counting

    print(f"Reading input file: {input_filepath}")
    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            for i, line in enumerate(infile):
                item = line.strip() # Remove leading/trailing whitespace
                if item: # Only count non-empty lines
                    item_counts[item] += 1
                # else: # Optional: Log skipped empty lines
                #     print(f"Debug: Skipping empty line at line number {i+1}")

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'", file=sys.stderr)
        sys.exit(1) # Exit with an error code
    except Exception as e:
        print(f"An error occurred during file reading: {e}", file=sys.stderr)
        sys.exit(1) # Exit with an error code

    # Print the results
    if not item_counts:
        print("No items found or counted in the input file.")
        return

    print("\nItem Counts:")
    # Sort items alphabetically for consistent output, or by count if preferred
    # For alphabetical sorting:
    # for item, count in sorted(item_counts.items()):
    # For sorting by count (most frequent first):
    for item, count in item_counts.most_common():
        print(f"- {item}: {count}")

# --- Main execution block ---
if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Counts the occurrences of each unique line (item) in a text file.",
        formatter_class=argparse.RawTextHelpFormatter
        )

    # Define command-line arguments
    parser.add_argument(
        "input_file",
        help="Path to the input text file containing the list of items (one per line)."
        )

    # Parse the arguments provided by the user
    args = parser.parse_args()

    # Call the main counting function
    count_items_in_file(args.input_file)
