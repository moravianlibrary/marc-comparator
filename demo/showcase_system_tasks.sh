#!/bin/bash
set -euo pipefail

APP_URL="http://localhost:8000"

# Colors for nicer output
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

pause() {
    echo -e "${YELLOW}Press any key to continue...${NC}"
    read -n1 -s
    echo
}

print_step() {
    echo -e "\n${CYAN}=== $1 ===${NC}\n"
}

wait_for_tasks() {
    sleep 5
    while true; do
        response=$(http --session=demo-admin --print=b POST "$APP_URL/tasks/search-own" \
            Content-Type:application/json \
            <<< '{"filters": {"status": ["Pending", "Started"]}}')

        count=$(echo "$response" | jq '.total')
        echo "Tasks still pending/running: $count. Checking again in 30 seconds..."

        if [ "$count" -eq 0 ]; then
            break
        fi

        sleep 30
    done
}

# Admin credentials
ADMIN_EMAIL="admin@mzk.cz"
ADMIN_PASSWORD="AdminPassword"

###############################################################################
# 1. Login as admin
###############################################################################
print_step "Logging in as admin"

http --session=demo-admin POST "$APP_URL/auth/login" \
    email="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD"

pause

###############################################################################
# 2. Refresh analytics
###############################################################################
print_step "Run analytics refresh"

http --session=demo-admin POST "$APP_URL/maintenance/refresh-analytics"

wait_for_tasks
echo "Analytics refresh completed."
echo

pause

###############################################################################
# 3. Rebuild search vectors
###############################################################################
print_step "Run search vectors rebuild"

http --session=demo-admin POST "$APP_URL/maintenance/rebuild-search-vectors"

wait_for_tasks
echo "Search vectors rebuild completed."
echo

pause

###############################################################################
# 4. Cleanup stale locks
###############################################################################
print_step "Run stale locks cleanup"

http --session=demo-admin POST "$APP_URL/maintenance/cleanup-stale-locks"

wait_for_tasks
echo "Stale locks cleanup completed."
echo

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
