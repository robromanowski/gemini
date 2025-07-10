import requests
import json
import os
import argparse
import sys # Import sys for sys.stdout.flush()

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
        print(f"Error fetching snapshot status: {e}", file=sys.stderr) # Print to stderr for clarity
        print(f"Response content: {e.response.text if e.response else 'N/A'}", file=sys.stderr)
        return None

# --- Re-Modified Function with EXTREME Debugging ---

def analyze_snapshot_status(snapshot_data, snapshot_id):
    """
    Analyzes the snapshot data and provides detailed and summary information.
    Includes EXTREME type checking and debug prints to diagnose 'str' object errors.
    """
    print(f"DEBUG: START analyze_snapshot_status for snapshot ID: {snapshot_id}", flush=True)

    if not isinstance(snapshot_data, dict) or 'snapshots' not in snapshot_data or not snapshot_data['snapshots']:
        print(f"DEBUG: snapshot_data type is {type(snapshot_data)}. Expected dict. Contents (first 200 chars): {str(snapshot_data)[:200]}", flush=True)
        print(f"Error: Invalid snapshot data format or empty 'snapshots' list.", flush=True)
        return

    snapshot_info = snapshot_data['snapshots'][0]
    print(f"DEBUG: snapshot_info type is {type(snapshot_info)}. Keys: {list(snapshot_info.keys()) if isinstance(snapshot_info, dict) else 'N/A'}", flush=True)
    if not isinstance(snapshot_info, dict):
        print(f"Error: 'snapshots' list item is not a dictionary. Received type: {type(snapshot_info)}. Value: {str(snapshot_info)[:200]}...", flush=True)
        return

    state = snapshot_info.get('state', 'UNKNOWN')
    start_time = snapshot_info.get('start_time_in_millis')
    end_time = snapshot_info.get('end_time_in_millis')

    shards_data = snapshot_info.get('shards', {})
    print(f"DEBUG: shards_data type is {type(shards_data)}", flush=True)
    if not isinstance(shards_data, dict):
        print(f"Warning: 'shards' data is not a dictionary. Defaulting to 0. Type: {type(shards_data)}. Value: {str(shards_data)[:200]}...", flush=True)
        shards_total = 0
        shards_successful = 0
        shards_failed = 0
    else:
        shards_total = shards_data.get('total', 0)
        shards_successful = shards_data.get('successful', 0)
        shards_failed = shards_data.get('failed', 0)

    print("\n--- Snapshot Overview ---", flush=True)
    print(f"Snapshot ID: {snapshot_id}", flush=True)
    print(f"State: {state}", flush=True)
    print(f"Start Time: {start_time}", flush=True)
    print(f"End Time: {end_time}", flush=True)
    print(f"Total Shards: {shards_total}", flush=True)
    print(f"Successful Shards: {shards_successful}", flush=True)
    print(f"Failed Shards: {shards_failed}", flush=True)

    overall_percentage = 0
    if shards_total > 0:
        overall_percentage = (shards_successful / shards_total) * 100
    print(f"Overall Progress: {overall_percentage:.2f}%", flush=True)

    print("\n--- Index Details ---", flush=True)
    raw_indices_info = snapshot_info.get('indices', {}) # Get the raw data, could be dict or list
    print(f"DEBUG: raw_indices_info type is {type(raw_indices_info)}", flush=True)
    
    processed_indices = []
    if isinstance(raw_indices_info, dict):
        print("DEBUG: Processing 'indices' as a dictionary.", flush=True)
        for index_name, index_data in raw_indices_info.items():
            print(f"DEBUG:   Current index_name from dict: '{index_name}'. index_data type: {type(index_data)}", flush=True)
            if not isinstance(index_data, dict):
                print(f"Warning: Index '{index_name}' data is not a dictionary as expected (from dict). Skipping. Type: {type(index_data)}. Value: {str(index_data)[:200]}...", flush=True)
                continue 
            processed_indices.append((index_name, index_data))
    elif isinstance(raw_indices_info, list):
        print("DEBUG: Processing 'indices' as a list.", flush=True)
        # NUCLEAR DEBUGGING: Print the entire raw_indices_info if it's a list
        print(f"DEBUG: Full raw_indices_info (as list) for inspection: {json.dumps(raw_indices_info, indent=2)}", flush=True)

        for i, index_data_item in enumerate(raw_indices_info):
            print(f"DEBUG:   Processing list item {i}.", flush=True)
            print(f"DEBUG:     index_data_item before check: type={type(index_data_item)}, repr={repr(index_data_item)[:200]}", flush=True)

            if not isinstance(index_data_item, dict):
                print(f"CRITICAL WARNING: List item {i} in 'indices' is NOT a dictionary. Type: {type(index_data_item)}. Value: {str(index_data_item)[:200]}...", flush=True)
                # This 'continue' should prevent the AttributeError if it's a string
                continue
            
            # --- THE EXACT LINE REPORTED IN TRACEBACK ---
            try:
                # Ensure we are using 'index', not 'ndex' if that was a local typo.
                # The traceback you provided said 'ndex', please double-check your local file.
                index_name = index_data_item.get('index', 'UNKNOWN_INDEX_NAME') 
                print(f"DEBUG:     Successfully got index name: '{index_name}'", flush=True)
            except AttributeError as e:
                print(f"CRITICAL ERROR: Encountered AttributeError on item {i} trying to get 'index' property. "
                      f"Expected dict, but object is type {type(index_data_item)}. Error: {e}. "
                      f"Value (repr): {repr(index_data_item)[:200]}", file=sys.stderr, flush=True)
                failed_indices += 1 
                continue 

            processed_indices.append((index_name, index_data_item))
    else:
        print(f"Error: 'indices' data is neither a dictionary nor a list. Type: {type(raw_indices_info)}. Value: {str(raw_indices_info)[:200]}...", flush=True)
        print("No index details can be processed.", flush=True)
        return

    if not processed_indices:
        print("No valid index details available in the snapshot information.", flush=True)
        return

    total_indices = len(processed_indices)
    completed_indices = 0
    failed_indices = 0 

    for index_name, index_data in processed_indices:
        print(f"DEBUG: Final loop processing index '{index_name}'. index_data type: {type(index_data)}", flush=True)
        if not isinstance(index_data, dict):
            print(f"CRITICAL ERROR: Processed index '{index_name}' data is NOT a dictionary after normalization. Type: {type(index_data)}. Value: {str(index_data)[:200]}...", flush=True)
            failed_indices += 1
            continue

        index_state = index_data.get('state', 'UNKNOWN')
        
        index_shards_data = index_data.get('shards', {})
        print(f"DEBUG:   Index '{index_name}' shards_data type: {type(index_shards_data)}", flush=True)
        if not isinstance(index_shards_data, dict):
            print(f"Warning: Index '{index_name}' 'shards' data is not a dictionary. Defaulting to 0. Type: {type(index_shards_data)}. Value: {str(index_shards_data)[:200]}...", flush=True)
            index_shards_total = 0
            index_shards_successful = 0
            index_shards_failed = 0
        else:
            index_shards_total = index_shards_data.get('total', 0)
            index_shards_successful = index_shards_data.get('successful', 0)
            index_shards_failed = index_shards_data.get('failed', 0)
            
        index_stats = index_data.get('stats', {})
        print(f"DEBUG:   Index '{index_name}' stats type: {type(index_stats)}", flush=True)
        if not isinstance(index_stats, dict):
            print(f"Warning: Index '{index_name}' 'stats' data is not a dictionary. Defaulting to 0. Type: {type(index_stats)}. Value: {str(index_stats)[:200]}...", flush=True)
            total_size = 0
            total_docs = 0
        else:
            total_size = index_stats.get('size_in_bytes', 0)
            total_docs = index_stats.get('number_of_documents', 0)

        print(f"\nIndex: {index_name}", flush=True)
        print(f"  State: {index_state}", flush=True)
        print(f"  Shards (Total/Successful/Failed): {index_shards_total}/{index_shards_successful}/{index_shards_failed}", flush=True)
        print(f"  Total Size: {total_size / (1024*1024):.2f} MB", flush=True)
        print(f"  Total Documents: {total_docs}", flush=True)

        if index_state == 'SUCCESS':
            completed_indices += 1
        elif index_state == 'FAILED':
            failed_indices += 1

    print(f"\n--- Summary of Indices ---", flush=True)
    print(f"Total Indices: {total_indices}", flush=True)
    print(f"Completed Indices: {completed_indices}", flush=True)
    print(f"Failed Indices: {failed_indices}", flush=True)
    print(f"Pending/In-progress Indices: {total_indices - completed_indices - failed_indices}", flush=True)

    if total_indices > 0:
        indices_completion_percentage = (completed_indices / total_indices) * 100
        print(f"Indices Completion Percentage: {indices_completion_percentage:.2f}%", flush=True)
    else:
        print("Indices Completion Percentage: N/A (No indices found)", flush=True)

    print(f"DEBUG: END analyze_snapshot_status", flush=True)


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

    if not args.username:
        parser.error("OpenSearch username not provided. Use --username or set OPENSEARCH_USERNAME environment variable.")
    if not args.password:
        parser.error("OpenSearch password not provided. Use --password or set OPENSEARCH_PASSWORD environment variable.")

    print(f"Checking status for snapshot '{args.snapshot_id}' in repository '{args.repository}'...", flush=True)

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
        print("Failed to retrieve snapshot status. Please check your parameters and network connectivity.", flush=True)
