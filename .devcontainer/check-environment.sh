#!/bin/bash
# DevContainer environment validation script
# This script checks for required files and environment variables
# and provides helpful messages about missing requirements

check_success=true

# Function to check for required file
check_required_file() {
    local file_path="$1"
    local description="$2"
    local auto_create="$3"
    
    if [ ! -f "$file_path" ]; then
        echo "⚠️  MISSING: $description ($file_path)"
        if [ "$auto_create" = "true" ]; then
            echo "   Creating default file..."
            touch "$file_path"
            echo "   ✅ Default file created"
        else
            echo "   ❌ Please create this file before continuing"
            check_success=false
        fi
    else
        echo "✅ FOUND: $description"
    fi
}

# Function to check for required directory
check_required_dir() {
    local dir_path="$1"
    local description="$2"
    local auto_create="$3"
    
    if [ ! -d "$dir_path" ]; then
        echo "⚠️  MISSING: $description ($dir_path)"
        if [ "$auto_create" = "true" ]; then
            echo "   Creating directory..."
            mkdir -p "$dir_path"
            echo "   ✅ Directory created"
        else
            echo "   ❌ Please create this directory before continuing"
            check_success=false
        fi
    else
        echo "✅ FOUND: $description"
    fi
}

# Function to check for required environment variable
check_env_var() {
    local var_name="$1"
    local description="$2"
    local required="$3"
    
    if [ -z "${!var_name}" ]; then
        if [ "$required" = "true" ]; then
            echo "⚠️  MISSING: $description ($var_name)"
            echo "   ❌ Please set this environment variable"
            check_success=false
        else
            echo "⚠️  OPTIONAL: $description ($var_name) - Not set"
        fi
    else
        echo "✅ SET: $description"
    fi
}

echo "========================================="
echo "DevContainer Environment Validation Check"
echo "========================================="

# Check required directories
check_required_dir "/workspace" "Workspace directory" "true"

# Check configuration files
check_required_file ".env" "Environment variables" "true"
check_required_file "requirements.txt" "Python requirements" "false"

# Check Redis setup
echo ""
echo "Redis Availability:"
if redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis is running correctly"
else
    echo "⚠️  Redis is not available"
    echo "   Some Redis-dependent functionality may not work"
fi

# Check optional environment variables
echo ""
echo "Optional Environment Variables:"
check_env_var "OPENAI_API_KEY" "OpenAI API Key" "false"
check_env_var "ANTHROPIC_API_KEY" "Anthropic API Key" "false"
check_env_var "GITHUB_TOKEN" "GitHub API Token" "false"
check_env_var "GCS_BUCKET_NAME" "Google Cloud Storage Bucket" "false"

echo ""
echo "========================================="
if [ "$check_success" = "true" ]; then
    echo "✅ Environment is ready"
else
    echo "⚠️  Some issues were found in your environment"
    echo "   See details above for recommended actions"
fi
echo "========================================="
