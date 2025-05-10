#!/bin/bash
# Script to update import statements from utils to ailf

# Function to update imports in a file
update_imports() {
    local file=$1
    
    # Skip files in the utils directory itself
    if [[ $file == *"/utils/"* ]]; then
        return
    fi
    
    # Skip binary files
    if file "$file" | grep -q "binary"; then
        return
    fi
    
    # Skip files that don't contain 'utils' imports
    if ! grep -q "from utils" "$file" && ! grep -q "import utils" "$file"; then
        return
    fi
    
    echo "Updating imports in $file"
    
    # Replace direct imports from utils with ailf
    sed -i 's/from utils\./from ailf\./g' "$file"
    sed -i 's/import utils\./import ailf\./g' "$file"
    
    # Handle try/except blocks for development imports
    # This is more complex and might need manual attention
    # Just flag them for now
    if grep -q "try:.*from utils" "$file" || grep -q "except ImportError" "$file"; then
        echo "  WARNING: $file contains try/except blocks for imports - may need manual attention"
    fi
}

# Find all Python files in the project (excluding utils directory)
find /workspaces/template-python-dev -type f -name "*.py" | grep -v "__pycache__" | while read -r file; do
    update_imports "$file"
done

echo "Import update complete. Please check the warnings for files that might need manual attention."
