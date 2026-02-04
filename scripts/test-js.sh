#!/bin/bash
# test-js.sh - Run skill tests using Node.js

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running skill tests...${NC}"
echo ""

# Check if specific test file was provided
TEST_FILE="$1"

# Run the test harness
node "$SCRIPT_DIR/test-harness.mjs" $TEST_FILE

echo ""
echo -e "${GREEN}Tests completed!${NC}"
