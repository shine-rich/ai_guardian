#!/bin/bash

echo "🔍 Checking for DROP rules in OUTPUT chain..."
rules=$(sudo iptables -L OUTPUT --line-numbers -n | grep DROP | awk '{print $1}' | tac)

if [ -z "$rules" ]; then
    echo "✅ No DROP rules found in OUTPUT chain."
    exit 0
fi

echo "🚫 Found DROP rules. Removing..."
for rule in $rules; do
    echo "❌ Deleting rule #$rule from OUTPUT chain..."
    sudo iptables -D OUTPUT $rule
done

echo "✅ All DROP rules removed from OUTPUT chain."
