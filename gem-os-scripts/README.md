# OpenSearch Snapshot Status Checker

This Python script allows you to check the detailed status of a specific OpenSearch snapshot, providing an overall summary and per-index progress, especially useful for snapshots involving many indices. It uses basic authentication to interact with your OpenSearch domain.

## Features

* Retrieves the status of a specific OpenSearch snapshot by ID.
* Provides an overall summary of the snapshot's state, including total, successful, and failed shards.
* Calculates an overall completion percentage based on successful shards.
* Offers detailed information for each index included in the snapshot, showing its individual state, shard breakdown, size, and document count.
* Summarizes index-level completion, failure, and in-progress counts.
* Supports runtime parameters for flexible usage without modifying the script file.
* Securely handles OpenSearch credentials via environment variables or command-line arguments.

## Prerequisites

* Python 3.x installed on your system.
* `requests` library: Used for making HTTP requests to the OpenSearch API.

    To install:
  ```
    pip install requests
  ```
## Configuration

The script primarily relies on command-line arguments. However, for OpenSearch username and password, it can also fall back to environment variables for enhanced security and convenience.

### Environment Variables (Optional but Recommended)

For secure handling of your OpenSearch credentials, it's highly recommended to set these as environment variables:

* `OPENSEARCH_USERNAME`: Your OpenSearch master username.
* `OPENSEARCH_PASSWORD`: Your OpenSearch master password.

Example (Linux/macOS):
```
export OPENSEARCH_USERNAME="your_opensearch_user"
export OPENSEARCH_PASSWORD="your_opensearch_password"
```

Example (Windows - Command Prompt):
```
set OPENSEARCH_USERNAME="your_opensearch_user"
set OPENSEARCH_PASSWORD="your_opensearch_password"
```

Example (Windows - PowerShell):
```
$env:OPENSEARCH_USERNAME="your_opensearch_user"
$env:OPENSEARCH_PASSWORD="your_opensearch_password"
```

## Usage

Run the script from your terminal, providing the necessary parameters.

Example command:
```
python check_opensearch_snapshot.py \
  --endpoint "[https://search-your-domain-xyz.us-east-1.es.amazonaws.com](https://search-your-domain-xyz.us-east-1.es.amazonaws.com)" \
  --repository "my-snapshot-repo" \
  --snapshot-id "my-daily-snapshot-2023-10-27" \
  --username "your_opensearch_user" \
  --password "your_opensearch_password"
```

### Command-line Arguments

| Flag | Full Name | Type | Required | Description |
| :--- | :-------- | :--- | :------- | :---------- |
| `-e` | `--endpoint` | str | Yes | The full endpoint URL of your OpenSearch domain. |
| `-r` | `--repository` | str | Yes | The name of the snapshot repository where the snapshot is stored. |
| `-s` | `--snapshot-id`| str | Yes | The ID of the specific snapshot you want to check. |
| `-u` | `--username` | str | No | Your OpenSearch master username. Falls back to `OPENSEARCH_USERNAME` environment variable. |
| `-p` | `--password` | str | No | Your OpenSearch master password. Falls back to `OPENSEARCH_PASSWORD` environment variable. |

Note: If `username` or `password` are not provided via command-line arguments, the script will attempt to retrieve them from the corresponding environment variables. If still not found, the script will exit with an error.

### Example Runs

1. Checking a Snapshot using Command-Line Arguments:

Command:
```
python check_opensearch_snapshot.py \
  -e "[https://search-example.us-east-1.es.amazonaws.com](https://search-example.us-east-1.es.amazonaws.com)" \
  -r "opensearch-backups" \
  -s "weekly-snapshot-2025-07-07" \
  -u "admin" \
  -p "yourStrongPassword"
```

2. Checking a Snapshot using Environment Variables for Credentials:

First, set your environment variables:
```
export OPENSEARCH_USERNAME="admin"
export OPENSEARCH_PASSWORD="yourStrongPassword"
```

Then run the script:
```
python check_opensearch_snapshot.py \
  --endpoint "[https://search-example.us-east-1.es.amazonaws.com](https://search-example.us-east-1.es.amazonaws.com)" \
  --repository "opensearch-backups" \
  --snapshot-id "daily-snapshot-2025-07-09"
```

### Expected Output Example (Snapshot In-Progress)

Checking status for snapshot 'my_daily_snapshot-2023-10-27' in repository 'my-snapshot-repo'...

```
--- Snapshot Overview ---
Snapshot ID: my_daily_snapshot-2023-10-27
State: IN_PROGRESS
Start Time: 1678886400000
End Time: None
Total Shards: 100
Successful Shards: 65
Failed Shards: 0
Overall Progress: 65.00%

--- Index Details ---

Index: logs-2023-10-26
  State: SUCCESS
  Shards (Total/Successful/Failed): 5/5/0
  Total Size: 1024.50 MB
  Total Documents: 5000000

Index: app-data-2023-10-27
  State: IN_PROGRESS
  Shards (Total/Successful/Failed): 10/7/0
  Total Size: 0.00 MB
  Total Documents: 0

... (other indices) ...

--- Summary of Indices ---
Total Indices: 4
Completed Indices: 1
Failed Indices: 0
Pending/In-progress Indices: 3
Indices Completion Percentage: 25.00%
```

The output will vary depending on the actual state of your snapshot (e.g., `SUCCESS`, `PARTIAL`, `FAILED`).

## Security Best Practices

* Avoid Hardcoding Credentials: Never hardcode your OpenSearch username and password directly into the script for production environments. Use environment variables or a dedicated secret management service (like AWS Secrets Manager) instead.
* Least Privilege: Ensure the OpenSearch user used by this script has only the necessary permissions to read snapshot information (typically `cluster:admin/snapshot/status` and `indices:admin/snapshot/status`).
