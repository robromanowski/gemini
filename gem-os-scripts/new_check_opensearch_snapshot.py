import requests
import json
import os
import argparse
import sys

# --- Functions (unchanged - get_snapshot_status_basic_auth) ---

def get_snapshot_status_basic_auth(opensearch_domain_endpoint, snapshot_repository_name, snapshot_id, username, password):
    """
    Retrieves the status of a specific OpenSearch snapshot using basic authentication.
    """
    snapshot_url = f'{opensearch_domain_endpoint}/_snapshot/{snapshot_repository_name}/{snapshot_id}'
    try:
        response = requests.get(snapshot_url, auth=(username, password))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching snapshot status: {e}", file=sys.stderr)
        print(f"Response content: {e.response.text if e.response else 'N/A'}", file=sys.stderr)
        return None

# --- Simplified and Corrected analyze_snapshot_status function ---

def analyze_snapshot_status(snapshot_data, snapshot_id):
    """
    Analyzes the snapshot data and provides detailed and summary information.
    Specifically handles 'indices' field as a dictionary of index details.
    """
    print(f"DEBUG: START analyze_snapshot_status for snapshot ID: {snapshot_id}", flush=True)

    if not isinstance(snapshot_data, dict) or 'snapshots' not in snapshot_data or not snapshot_data['snapshots']:
        print(f"Error: Invalid snapshot data format. Expected dictionary with 'snapshots' key. Received type: {type(snapshot_data)}", flush=True)
        if isinstance(snapshot_data, str):
            print(f"Received data (first 200 chars): {snapshot_data[:200]}...", flush=True)
        return

    snapshot_info = snapshot_data['snapshots'][0]
    print(f"DEBUG: snapshot_info type is {type(snapshot_info)}. Keys: {list(snapshot_info.keys()) if isinstance(snapshot_info, dict) else 'N/A'}", flush=True)
    if not isinstance(snapshot_info, dict):
        print(f"Error: 'snapshots' list item is not a dictionary. Received type: {type(snapshot_info)}. Value: {str(snapshot_info)[:200]}...", flush=True)
        return

    state = snapshot_info.get('state', 'UNKNOWN')
    start_time = snapshot_info.get('stats', {}).get('start_time_in_millis') # Access via 'stats'
    end_time = snapshot_info.get('stats', {}).get('time_in_millis') # This is actually 'time_in_millis' for duration
    
    # Calculate end_time if start_time and time_in_millis are present
    formatted_end_time = None
    if start_time is not None and end_time is not None:
        actual_end_millis = start_time + end_time
        # You might want to convert these millis timestamps to human-readable datetime
        # Example: datetime.datetime.fromtimestamp(actual_end_millis / 1000).strftime('%Y-%m-%d %H:%M:%S')
        formatted_end_time = f"{actual_end_millis} (calculated)"
    else:
        # If 'stats.time_in_millis' is not the snapshot end time, this needs adjustment based on actual API.
        # Often, finished snapshots have a top-level 'end_time_in_millis' directly.
        # Let's check for 'end_time_in_millis' at top level as well.
        top_level_end_time = snapshot_info.get('end_time_in_millis')
        if top_level_end_time:
            formatted_end_time = top_level_end_time
        elif end_time: # Use time_in_millis if it's the only end-time like field
            formatted_end_time = end_time


    shards_stats = snapshot_info.get('shards_stats', {}) # Corrected: 'shards_stats' at top level
    print(f"DEBUG: shards_stats type is {type(shards_stats)}", flush=True)
    if not isinstance(shards_stats, dict):
        print(f"Warning: 'shards_stats' data is not a dictionary. Defaulting to 0. Type: {type(shards_stats)}. Value: {str(shards_stats)[:200]}...", flush=True)
        shards_total = 0
        shards_successful = 0
        shards_failed = 0
    else:
        shards_total = shards_stats.get('total', 0)
        shards_successful = shards_stats.get('done', 0) # 'done' for successful in shards_stats
        shards_failed = shards_stats.get('failed', 0)

    print("\n--- Snapshot Overview ---", flush=True)
    print(f"Snapshot ID: {snapshot_id}", flush=True)
    print(f"State: {state}", flush=True)
    print(f"Start Time: {start_time}", flush=True)
    print(f"End Time (calculated/actual): {formatted_end_time}", flush=True) # Use the formatted end time
    print(f"Total Shards: {shards_total}", flush=True)
    print(f"Successful Shards: {shards_successful}", flush=True)
    print(f"Failed Shards: {shards_failed}", flush=True)

    overall_percentage = 0
    if shards_total > 0:
        overall_percentage = (shards_successful / shards_total) * 100
    print(f"Overall Progress: {overall_percentage:.2f}%", flush=True)

    print("\n--- Index Details ---", flush=True)
    raw_indices_info = snapshot_info.get('indices', {})
    print(f"DEBUG: raw_indices_info type is {type(raw_indices_info)}", flush=True)
    
    # Based on your Dev Tools output, 'indices' is a dictionary of dictionaries
    if not isinstance(raw_indices_info, dict):
        print(f"Error: 'indices' data is not a dictionary as expected for detailed analysis. Type: {type(raw_indices_info)}. Value: {str(raw_indices_info)[:200]}...", flush=True)
        print("No index details can be processed.", flush=True)
        return

    total_indices = len(raw_indices_info)
    completed_indices = 0
    failed_indices = 0

    for index_name, index_data in raw_indices_info.items():
        print(f"DEBUG: Processing index '{index_name}'. index_data type: {type(index_data)}", flush=True)
        if not isinstance(index_data, dict):
            print(f"Warning: Index '{index_name}' data is not a dictionary. Skipping details for this index. Type: {type(index_data)}. Value: {str(index_data)[:200]}...", flush=True)
            # We skip detailed processing for this malformed index, but still count it
            failed_indices += 1 # Or just count it as 'unparseable'
            continue

        # For index state, we often infer SUCCESS if shards are all done.
        # OpenSearch 1.x / Elasticsearch 7.x snapshot status doesn't always have a top-level 'state' per index.
        # We can derive it from shards_stats.
        index_shards_stats = index_data.get('shards_stats', {})
        
        # Check if index_shards_stats is a dictionary before getting keys
        if not isinstance(index_shards_stats, dict):
            print(f"Warning: Index '{index_name}' 'shards_stats' data is not a dictionary. Skipping detailed shard analysis. Type: {type(index_shards_stats)}", flush=True)
            index_state = "UNKNOWN_SHARDS_INFO"
            index_shards_total = 0
            index_shards_successful = 0
            index_shards_failed = 0
        else:
            index_shards_total = index_shards_stats.get('total', 0)
            index_shards_successful = index_shards_stats.get('done', 0) # 'done' for successful
            index_shards_failed = index_shards_stats.get('failed', 0)

            if index_shards_total > 0 and index_shards_successful == index_shards_total and index_shards_failed == 0:
                index_state = "SUCCESS"
            elif index_shards_failed > 0:
                index_state = "FAILED"
            elif index_shards_total > 0 and index_shards_successful < index_shards_total:
                index_state = "IN_PROGRESS"
            else:
                index_state = "UNKNOWN"

        index_stats = index_data.get('stats', {})
        print(f"DEBUG:   Index '{index_name}' stats type: {type(index_stats)}", flush=True)
        if not isinstance(index_stats, dict):
            print(f"Warning: Index '{index_name}' 'stats' data is not a dictionary. Defaulting to 0. Type: {type(index_stats)}. Value: {str(index_stats)[:200]}...", flush=True)
            total_size = 0
            total_docs = 0
        else:
            total_size = index_stats.get('total', {}).get('size_in_bytes', 0) # stats.total.size_in_bytes
            # OpenSearch 1.x / Elasticsearch 7.x snapshot status doesn't typically report number_of_documents here.
            # This would usually come from a _cat/indices API.
            total_docs = "N/A" # Default to N/A as it's not in snapshot status

        print(f"\nIndex: {index_name}", flush=True)
        print(f"  State: {index_state}", flush=True)
        print(f"  Shards (Total/Successful/Failed): {index_shards_total}/{index_shards_successful}/{index_shards_failed}", flush=True)
        print(f"  Total Size: {total_size / (1024*1024):.2f} MB", flush=True)
        print(f"  Total Documents: {total_docs}", flush=True) # Will be N/A

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
