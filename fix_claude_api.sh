#!/bin/bash

# Fix claude_api references in agent files
echo "Fixing claude_api references in agent files..."

# Step 1: Update imports in all agent files
for file in agents/*.py; do
    echo "Processing imports in $file"
    # Replace "from models.claude import claude_api" with "from models.claude import get_claude_api"
    sed -i '' 's/from models\.claude import claude_api/from models.claude import get_claude_api/g' "$file"
done

# Step 2: Update claude_api references in all agent files
for file in agents/*.py; do
    echo "Processing claude_api references in $file"
    # Replace "claude_api.user_message" with "get_claude_api().user_message"
    sed -i '' 's/claude_api\.user_message/get_claude_api().user_message/g' "$file"
    # Replace "claude_api.complete_with_retry" with "get_claude_api().complete_with_retry"
    sed -i '' 's/claude_api\.complete_with_retry/get_claude_api().complete_with_retry/g' "$file"
    # Replace any other claude_api method calls
    sed -i '' 's/claude_api\./get_claude_api()./g' "$file"
done

echo "Done fixing claude_api references" 