#!/bin/bash

# Base log directory
BASE_DIR="/home/andrew/logs"
TODAY=$(date +"%Y-%m-%d")
YEAR=$(date -d "$TODAY" +"%Y")
MONTH=$(date -d "$TODAY" +"%m")
LOG_DIR="$BASE_DIR/$YEAR/$MONTH"

# Ensure directory exists
mkdir -p "$LOG_DIR"

echo "Creating demo logs in: $LOG_DIR"

# Templates
SUCCESS_LOG="# Step 5. Success"
FAIL_LOG="# Step 5. Failed"

# Generate logs for past 5 days
for i in {0..4}; do
    DATE=$(date -d "$TODAY - $i days" +"%Y-%m-%d_%H%M%S")
    FILE="$LOG_DIR/sync-backups.sh-$DATE.log"

    if (( RANDOM % 5 == 0 )); then
        echo -e "$FAIL_LOG\n\nDetails: Network issue." > "$FILE"
    else
        echo -e "$SUCCESS_LOG\n\nDetails: Snapshot uploaded." > "$FILE"
    fi

    echo "Created: $FILE"
done

echo "✅ Demo backup logs created."
