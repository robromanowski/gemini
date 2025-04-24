import csv
import re
import argparse
import os

def parse_ansible_output(input_filepath, output_filepath):
    """
    Parses Ansible output containing file listings and generates a CSV file,
    including the server name associated with each file/directory.

    Args:
        input_filepath (str): Path to the input file containing Ansible output.
        output_filepath (str): Path for the generated CSV file.
    """

    # Regex to identify the server line (e.g., "servername.domain.com | STATUS | ...")
    # Captures the server name part before the first space or pipe.
    server_line_regex = re.compile(r"^([\w.-]+)\s*\|.*>>$")

    # Regex to find lines with file/dir listings (like ls -l output)
    # It looks for permissions, link count, owner, group, size, date parts, and filename.
    # It tries to robustly capture the filename at the end of the line.
    # Handles variations in date format (e.g., "Apr 24 14:42" or "Sep 20  2023")
    line_regex = re.compile(
        # Permissions (d or - followed by rwx-) and link count
        r"^[drwx-]{10}\s+\d+\s+"
        # Owner and group (can contain numbers or names)
        r"\S+\s+\S+\s+"
        # Size
        r"\d+\s+"
        # Date (Month Day Year/Time) - allowing for variable spacing
        r"\w+\s+\d+\s+[\d:]{4,5}\s+"
        # Capture the rest of the line, which should be the filename
        r"(.+)$"
    )


    # Regex to parse the specific filename structure:
    # tech_appl_default_user_{user}_.{env_type}_{name}.yml
    filename_regex = re.compile(
        r"^tech_appl_default_user_" # Static prefix
        r"([a-zA-Z0-9]+)_"         # Capture group 1: user (alphanumeric)
        r"\."                       # Literal dot
        r"([a-zA-Z0-9_]+)_"         # Capture group 2: env_type_raw (alphanumeric and underscore)
        r"([a-zA-Z0-9-]+)"         # Capture group 3: name (alphanumeric and hyphen)
        r"\.yml$"                   # Suffix .yml
        )

    extracted_data = []
    current_server = "UnknownServer" # Default if no server line found before first file

    print(f"Reading input file: {input_filepath}")
    try:
        with open(input_filepath, 'r', encoding='utf-8') as infile:
            for i, line in enumerate(infile):
                line = line.strip()
                if not line: # Skip empty lines
                    continue

                # Check if the line contains a server name
                server_match = server_line_regex.match(line)
                if server_match:
                    current_server = server_match.group(1)
                    # print(f"Debug: Line {i+1}: Found server: '{current_server}'") # Optional Debugging
                    continue # Move to the next line after finding a server

                # Attempt to match the file/directory listing format
                line_match = line_regex.match(line)
                if line_match:
                    # Extract the potential filename part
                    filename = line_match.group(1).strip()
                    # print(f"Debug: Line {i+1}: Found potential filename: '{filename}'") # Optional Debugging

                    # Attempt to parse the extracted filename
                    filename_match = filename_regex.match(filename)
                    if filename_match:
                        user = filename_match.group(1)
                        env_type_raw = filename_match.group(2)
                        name = filename_match.group(3)

                        # Construct the path as specified
                        path = f"/tech/appl/default/user/{user}"

                        # Standardize env_type (e.g., 'conda_envs' -> 'conda_env')
                        env_type = "conda_env" if env_type_raw.lower().startswith("conda_envs") else env_type_raw

                        # Add the parsed data to our list, including the current server
                        extracted_data.append({
                            'path': path,
                            'user': user,
                            'env_type': env_type,
                            'name': name,
                            'server': current_server # Add the server name here
                        })
                        # print(f"Debug: Line {i+1}: Parsed: path={path}, user={user}, env_type={env_type}, name={name}, server={current_server}") # Optional Debugging
                    # else: # Optional Debugging
                        # print(f"Debug: Line {i+1}: Filename '{filename}' did not match expected pattern.")
                # else: # Optional Debugging (Lines that are neither server nor file listing)
                    # print(f"Debug: Line {i+1}: Skipping line (no file/dir/server match): '{line}'")


    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'")
        return
    except Exception as e:
        print(f"An error occurred during file reading or parsing: {e}")
        return

    # Write data to CSV
    if not extracted_data:
        print("Warning: No matching data found in the input file to write to CSV.")
        return

    print(f"Writing data to CSV file: {output_filepath}")
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_filepath)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        with open(output_filepath, 'w', newline='', encoding='utf-8') as outfile:
            # Define the exact header order as requested, including 'server'
            fieldnames = ['path', 'user', 'env_type', 'name', 'server']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)

            # Write the header row
            writer.writeheader()
            # Write the data rows
            writer.writerows(extracted_data)

        print(f"Successfully created CSV file: {output_filepath}")
        print(f"Total records written: {len(extracted_data)}")

    except IOError as e:
        print(f"Error: Could not write to output file '{output_filepath}'. Reason: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CSV writing: {e}")

# --- Main execution block ---
if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Parse Ansible file listing output (like ls -l) and generate a CSV file with structured data, including server names.",
        formatter_class=argparse.RawTextHelpFormatter # Preserve formatting in help text
        )

    # Define command-line arguments
    parser.add_argument(
        "input_file",
        help="Path to the input text file containing the Ansible output."
        )
    parser.add_argument(
        "output_file",
        help="Path for the generated CSV output file."
        )

    # Parse the arguments provided by the user
    args = parser.parse_args()

    # Call the main parsing function with the provided arguments
    parse_ansible_output(args.input_file, args.output_file)
