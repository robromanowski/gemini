import requests
import json
import os
import argparse

# --- Functions (unchanged - get_snapshot_status_basic_auth) ---

def get_snapshot_status_basic_auth(opensearch_domain_endpoint, snapshot_repository_name, snapshot_id, username, password):
    """
    Retrieves the status of a specific OpenSearch snapshot using basic authentication.
    """
    snapshot_url = f'{opensearch_domain_endpoint}/_snapshot/{snapshot_repository_name}/{snapshot_id}'
    try:import requests
import json
import os
import argparse

# --- Functions (unchanged - get_snapshot_status_basic_auth) ---

def get_snapshot_status_basic_auth(opensearch_domain_endpoint, snapshot_repository_name, snapshot_id, username, password):
    """
    Retrieves the status of a specific OpenSearch snapshot using basic authentication.
    """
    snapshot_url = f'{opensearch_domain_endpoint}/_snapshot/{snapshot_repository_name}/{snapshot_id}'
    try:
        response = requests.get(snapshot_url, auth=(username, password))
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching snapshot status: {e}")
        print(f"Response content: {e.response.text if e.response else 'N/A'}")
        return None

# --- Re-Modified Function with more robust type checking ---

def analyze_snapshot_status(snapshot_data, snapshot_id):
    """
    Analyzes the snapshot data and provides detailed and summary information.
    Handles 'indices' field being a dictionary or a list.
    Adds type checking to prevent 'str' object has no attribute 'get' errors.
    """
    if not isinstance(snapshot_data, dict) or 'snapshots' not in snapshot_data or not snapshot_data['snapshots']:
        print(f"Error: Invalid snapshot data format. Expected dictionary with 'snapshots' key. Received type: {type(snapshot_data)}")
        if isinstance(snapshot_data, str):
            print(f"Received data (first 200 chars): {snapshot_data[:200]}...")
        return

    snapshot_info = snapshot_data['snapshots'][0]
    if not isinstance(snapshot_info, dict):
        print(f"Error: 'snapshots' list item is not a dictionary. Received type: {type(snapshot_info)}")
        if isinstance(snapshot_info, str):
            print(f"Snapshot info (first 200 chars): {snapshot_info[:200]}...")
        return

    state = snapshot_info.get('state', 'UNKNOWN')
    start_time = snapshot_info.get('start_time_in_millis')
    end_time = snapshot_info.get('end_time_in_millis')

    # Add type checking for 'shards'
    shards_data = snapshot_info.get('shards', {})
    if not isinstance(shards_data, dict):
        print(f"Warning: 'shards' data is not a dictionary. Defaulting to 0. Type: {type(shards_data)}")
        shards_total = 0
        shards_successful = 0
        shards_failed = 0
    else:
        shards_total = shards_data.get('total', 0)
        shards_successful = shards_data.get('successful', 0)
        shards_failed = shards_data.get('failed', 0)

    print("\n--- Snapshot Overview ---")
    print(f"Snapshot ID: {snapshot_id}")
    print(f"State: {state}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Total Shards: {shards_total}")
    print(f"Successful Shards: {shards_successful}")
    print(f"Failed Shards: {shards_failed}")

    overall_percentage = 0
    if shards_total > 0:
        overall_percentage = (shards_successful / shards_total) * 100
    print(f"Overall Progress: {overall_percentage:.2f}%")

    print("\n--- Index Details ---")
    raw_indices_info = snapshot_info.get('indices', {}) # Get the raw data, could be dict or list
    
    # Normalize indices_info to always be a list of (name, data) tuples
    processed_indices = []
    if isinstance(raw_indices_info, dict):
        for index_name, index_data in raw_indices_info.items():
            if not isinstance(index_data, dict):
                print(f"Warning: Index '{index_name}' data is not a dictionary. Skipping. Type: {type(index_data)}")
                continue # Skip this index if its data is malformed
            processed_indices.append((index_name, index_data))
    elif isinstance(raw_indices_info, list):
        for index_data_item in raw_indices_info:
            if not isinstance(index_data_item, dict):
                print(f"Warning: List item in 'indices' is not a dictionary. Skipping. Type: {type(index_data_item)}")
                continue # Skip malformed list items
            # Assuming if it's a list, each item is a dict containing 'index' name and other details
            index_name = index_data_item.get('index', 'UNKNOWN_INDEX')
            processed_indices.append((index_name, index_data_item))
    else:
        print(f"Error: 'indices' data is neither a dictionary nor a list. Type: {type(raw_indices_info)}")
        print("No index details can be processed.")
        return # Exit if indices data is fundamentally wrong

    if not processed_indices:
        print("No valid index details available in the snapshot information.")
        return

    total_indices = len(processed_indices)
    completed_indices = 0
    failed_indices = 0

    for index_name, index_data in processed_indices: # Iterate over the normalized and validated list
        # Add type checking for index_data before calling .get()
        if not isinstance(index_data, dict):
            print(f"Critical Error: Processed index '{index_name}' data is not a dictionary. Skipping. Type: {type(index_data)}")
            failed_indices += 1 # Count it as failed for summary purposes
            continue

        index_state = index_data.get('state', 'UNKNOWN')
        
        # Add type checking for shards_data within index_data
        index_shards_data = index_data.get('shards', {})
        if not isinstance(index_shards_data, dict):
            print(f"Warning: Index '{index_name}' 'shards' data is not a dictionary. Defaulting to 0. Type: {type(index_shards_data)}")
            index_shards_total = 0
            index_shards_successful = 0
            index_shards_failed = 0
        else:
            index_shards_total = index_shards_data.get('total', 0)
            index_shards_successful = index_shards_data.get('successful', 0)
            index_shards_failed = index_shards_data.get('failed', 0)
            
        # Add type checking for index_stats
        index_stats = index_data.get('stats', {})
        if not isinstance(index_stats, dict):
            print(f"Warning: Index '{index_name}' 'stats' data is not a dictionary. Defaulting to 0. Type: {type(index_stats)}")
            total_size = 0
            total_docs = 0
        else:
            total_size = index_stats.get('size_in_bytes', 0)
            total_docs = index_stats.get('number_of_documents', 0)

        print(f"\nIndex: {index_name}")
        print(f"  State: {index_state}")
        print(f"  Shards (Total/Successful/Failed): {index_shards_total}/{index_shards_successful}/{index_shards_failed}")
        print(f"  Total Size: {total_size / (1024*1024):.2f} MB")
        print(f"  Total Documents: {total_docs}")

        if index_state == 'SUCCESS':
            completed_indices += 1
        elif index_state == 'FAILED':
            failed_indices += 1

    print(f"\n--- Summary of Indices ---")
    print(f"Total Indices: {total_indices}")
    print(f"Completed Indices: {completed_indices}")
    print(f"Failed Indices: {failed_indices}")
    print(f"Pending/In-progress Indices: {total_indices - completed_indices - failed_indices}")

    if total_indices > 0:
        indices_completion_percentage = (completed_indices / total_indices) * 100
        print(f"Indices Completion Percentage: {indices_completion_percentage:.2f}%")
    else:
        print("Indices Completion Percentage: N/A (No indices found)")

# --- Main Execution (unchanged) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check AWS OpenSearch snapshot status with basic authentication.")

    parser.add_argument('--endpoint', '-e', type=str, required=True,
                        help='The OpenSearch domain endpoint (e.g., https://search-your-domain-xyz.us-east-1.es.amazonaws.com)')
    parser.add_argument('--repository', '-r', type=str, required=True,
                        help='The name of the snapshot repository (e.g., my-snapshot-repo)')
    parser.add_argument('--snapshot-id', '-s', type=str, required=True,
                        help='The ID of the snapshot to check (e.g., my-daily-snapshot-2023-10-27)')
    parser.add_argument('--username', '-u', type=str, default=os.environ.get('OPENSEARCH_USERNAME'),
                        help='OpenSearch master username. Can also be set via OPENSEARCH_USERNAME environment variable.')
    parser.add_argument('--password', '-p', type=str, default=os.environ.get('OPENSEARCH_PASSWORD'),
                        help='OpenSearch master password. Can also be set via OPENSEARCH_PASSWORD environment variable.')

    args = parser.parse_args()

    # Validate that username and password are provided either via args or environment variables
    if not args.username:
        parser.error("OpenSearch username not provided. Use --username or set OPENSEARCH_USERNAME environment variable.")
    if not args.password:
        parser.error("OpenSearch password not provided. Use --password or set OPENSEARCH_PASSWORD environment variable.")

    print(f"Checking status for snapshot '{args.snapshot_id}' in repository '{args.repository}'...")

    snapshot_status = get_snapshot_status_basic_auth(
        args.endpoint,
        args.repository,
        args.snapshot_id,
        args.username,
        args.password
    )

    if snapshot_status:
        analyze_snapshot_status(snapshot_status, args.snapshot_id)
    else:
        print("Failed to retrieve snapshot status. Please check your parameters and network connectivity.")
        response = requests.get(snapshot_url, auth=(username, password))
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching snapshot status: {e}")
        print(f"Response content: {e.response.text if e.response else 'N/A'}")
        return None

# --- Modified Function ---

def analyze_snapshot_status(snapshot_data, snapshot_id):
    """
    Analyzes the snapshot data and provides detailed and summary information.
    Handles 'indices' field being a dictionary or a list.
    """
    if not snapshot_data or 'snapshots' not in snapshot_data or not snapshot_data['snapshots']:
        print("No snapshot data found or snapshot ID might be incorrect.")
        return

    snapshot_info = snapshot_data['snapshots'][0]
    state = snapshot_info.get('state', 'UNKNOWN')
    start_time = snapshot_info.get('start_time_in_millis')
    end_time = snapshot_info.get('end_time_in_millis')
    shards_total = snapshot_info.get('shards', {}).get('total', 0)
    shards_successful = snapshot_info.get('shards', {}).get('successful', 0)
    shards_failed = snapshot_info.get('shards', {}).get('failed', 0)

    print("\n--- Snapshot Overview ---")
    print(f"Snapshot ID: {snapshot_id}")
    print(f"State: {state}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Total Shards: {shards_total}")
    print(f"Successful Shards: {shards_successful}")
    print(f"Failed Shards: {shards_failed}")

    overall_percentage = 0
    if shards_total > 0:
        overall_percentage = (shards_successful / shards_total) * 100
    print(f"Overall Progress: {overall_percentage:.2f}%")

    print("\n--- Index Details ---")
    raw_indices_info = snapshot_info.get('indices', {}) # Get the raw data, could be dict or list
    
    # Normalize indices_info to always be a list of (name, data) tuples
    processed_indices = []
    if isinstance(raw_indices_info, dict):
        for index_name, index_data in raw_indices_info.items():
            processed_indices.append((index_name, index_data))
    elif isinstance(raw_indices_info, list):
        for index_data_item in raw_indices_info:
            # Assuming if it's a list, each item is a dict containing 'index' name and other details
            # This is a common format for lists of indices.
            index_name = index_data_item.get('index', 'UNKNOWN_INDEX')
            processed_indices.append((index_name, index_data_item))
    
    if not processed_indices:
        print("No index details available in the snapshot information.")
        return

    total_indices = len(processed_indices)
    completed_indices = 0
    failed_indices = 0

    for index_name, index_data in processed_indices: # Now iterate over the normalized list
        index_state = index_data.get('state', 'UNKNOWN')
        index_shards_total = index_data.get('shards', {}).get('total', 0)
        index_shards_successful = index_data.get('shards', {}).get('successful', 0)
        index_shards_failed = index_data.get('shards', {}).get('failed', 0)
        index_stats = index_data.get('stats', {})
        total_size = index_stats.get('size_in_bytes', 0)
        total_docs = index_stats.get('number_of_documents', 0)

        print(f"\nIndex: {index_name}")
        print(f"  State: {index_state}")
        print(f"  Shards (Total/Successful/Failed): {index_shards_total}/{index_shards_successful}/{index_shards_failed}")
        print(f"  Total Size: {total_size / (1024*1024):.2f} MB")
        print(f"  Total Documents: {total_docs}")

        if index_state == 'SUCCESS':
            completed_indices += 1
        elif index_state == 'FAILED':
            failed_indices += 1

    print(f"\n--- Summary of Indices ---")
    print(f"Total Indices: {total_indices}")
    print(f"Completed Indices: {completed_indices}")
    print(f"Failed Indices: {failed_indices}")
    print(f"Pending/In-progress Indices: {total_indices - completed_indices - failed_indices}")

    if total_indices > 0:
        indices_completion_percentage = (completed_indices / total_indices) * 100
        print(f"Indices Completion Percentage: {indices_completion_percentage:.2f}%")
    else:
        print("Indices Completion Percentage: N/A (No indices found)")


# --- Main Execution (unchanged) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check AWS OpenSearch snapshot status with basic authentication.")

    parser.add_argument('--endpoint', '-e', type=str, required=True,
                        help='The OpenSearch domain endpoint (e.g., https://search-your-domain-xyz.us-east-1.es.amazonaws.com)')
    parser.add_argument('--repository', '-r', type=str, required=True,
                        help='The name of the snapshot repository (e.g., my-snapshot-repo)')
    parser.add_argument('--snapshot-id', '-s', type=str, required=True,
                        help='The ID of the snapshot to check (e.g., my-daily-snapshot-2023-10-27)')
    parser.add_argument('--username', '-u', type=str, default=os.environ.get('OPENSEARCH_USERNAME'),
                        help='OpenSearch master username. Can also be set via OPENSEARCH_USERNAME environment variable.')
    parser.add_argument('--password', '-p', type=str, default=os.environ.get('OPENSEARCH_PASSWORD'),
                        help='OpenSearch master password. Can also be set via OPENSEARCH_PASSWORD environment variable.')

    args = parser.parse_args()

    # Validate that username and password are provided either via args or environment variables
    if not args.username:
        parser.error("OpenSearch username not provided. Use --username or set OPENSEARCH_USERNAME environment variable.")
    if not args.password:
        parser.error("OpenSearch password not provided. Use --password or set OPENSEARCH_PASSWORD environment variable.")

    print(f"Checking status for snapshot '{args.snapshot_id}' in repository '{args.repository}'...")

    snapshot_status = get_snapshot_status_basic_auth(
        args.endpoint,
        args.repository,
        args.snapshot_id,
        args.username,
        args.password
    )

    if snapshot_status:
        analyze_snapshot_status(snapshot_status, args.snapshot_id)
    else:
        print("Failed to retrieve snapshot status. Please check your parameters and network connectivity.")
