#!/bin/bash

# Global vars
CLOUD="remote:backups-$(hostname)"
BTRFS_SUBVOL="/mnt/store/backups"
SNAPSHOTS_DIR="/mnt/store"
LOGS_DIR="/home/scribe/logs"

#DATE=$(date +"%Y-%m-%d_%H%M%S")
DATE="2025-04-13_223344"
# Calculate snapshot filename
SNAPSHOT="$SNAPSHOTS_DIR/snapshot-$DATE"

# Calculate log filename
YEAR=${DATE:0:4}
MONTH=${DATE:5:2}
LOG="$LOGS_DIR/$YEAR/$MONTH/$(basename "$0")-$DATE.log"

echo -e "Current log file is:\n  \"$LOG\""

# Make sure the directory structure for the log file exists
[ ! -d "$LOGS_DIR/$YEAR/$MONTH" ] && mkdir -p "$LOGS_DIR/$YEAR/$MONTH"

# Create a read-only snapshot
echo -e "\n#\n# Step 1. Creating read-only snapshot \"$SNAPSHOT\"\n#\n" 2>&1 | tee -a "$LOG"
btrfs subvolume snapshot -r "$BTRFS_SUBVOL" "$SNAPSHOT" 2>&1 | tee -a "$LOG"
[ ! $? -eq 0 ] && exit 1

# Send to CLOUD
echo -e "\n#\n# Step 2. Sending to cloud. From \"$SNAPSHOT\" to \"$CLOUD\"\n#\n" 2>&1 | tee -a "$LOG"
rclone sync "$SNAPSHOT" "$CLOUD" --log-level INFO 2>&1 | tee -a "$LOG"
[ ! $? -eq 0 ] && exit 1

# Make snapshot writable / deletable
echo -e "\n#\n# Step 3. Removing read-only property from snapshot \"$SNAPSHOT\"\n#\n" 2>&1 | tee -a "$LOG"
btrfs property set -ts "$SNAPSHOT" ro false 2>&1 | tee -a "$LOG"
[ ! $? -eq 0 ] && exit 1

# Delete the snapshot
echo -e "\n#\n# Step 4. Deleting snapshot \"$SNAPSHOT\"\n#\n" 2>&1 | tee -a "$LOG"
btrfs subvolume delete "$SNAPSHOT" 2>&1 | tee -a "$LOG"
[ ! $? -eq 0 ] && exit 1

echo -e "\n#\n# Step 5. Success\n#\n" >> "$LOG"
