#!/bin/bash

# Fix relative imports in all agent files
echo "Fixing imports in agent files..."

# Replace relative imports with absolute imports in all Python files in the agents directory
for file in agents/*.py; do
    echo "Processing $file"
    # Replace ..config with config
    sed -i '' 's/from \.\./from /g' "$file"
done

echo "Done fixing imports" 