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

# Admin credentials
ADMIN_EMAIL="admin@mzk.cz"
ADMIN_PASSWORD="AdminPassword"

###############################################################################
# 1. Login as admin
###############################################################################
print_step "Logging in as admin"

http --form POST "$APP_URL/auth/login" \
    username="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD"

ADMIN_TOKEN=$(http --form --print=b POST "$APP_URL/auth/login" \
    username="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD" | jq -r .access_token)

pause

###############################################################################
# 2. Recreate indexes
###############################################################################
print_step "Run recreating of indexes"

http POST "$APP_URL/system/recreate-indexes" \
    "Authorization: Bearer $ADMIN_TOKEN"

sleep 5

ES_TASKS_QUERY_JSON=$(cat <<'EOF'
{
  "query": {
    "bool": {
      "should": [
        { "term": { "status": "Pending" } },
        { "term": { "status": "Started" } }
      ]
    }
  }
}
EOF
)

while true; do
    response=$(http POST "$APP_URL/tasks/search-own" \
        "Authorization: Bearer $ADMIN_TOKEN" \
        Content-Type:application/json \
        <<< "$ES_TASKS_QUERY_JSON")

    count=$(echo "$response" | jq '.hits.total.value')
    echo "Tasks still pending/running: $count. Checking again in 30 seconds..."

    if [ "$count" -eq 0 ]; then
        break
    fi

    sleep 30
done

echo "Recreating of indexes completed."
echo

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
