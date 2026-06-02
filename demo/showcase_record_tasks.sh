#!/bin/bash
set -euo pipefail

APP_URL="http://localhost:8000"

# Colors for nicer output
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

pause() {
    echo -e "${YELLOW}Press any key to continue...${NC}"
    [[ -t 0 ]] && read -n1 -s
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

http --ignore-stdin --session=demo-admin POST "$APP_URL/auth/login" \
    email="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD"

pause

###############################################################################
# 2. Set Authority Linking settings
###############################################################################
print_step "Setting Authority Linking settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "knihovny-cz": {
    "api_url": "https://www.knihovny.cz/api/v1",
    "mappings": [
      {
        "base": "MZK01",
        "id_template": "mzk.MZK01-{system_number}",
        "pattern": "^mzk\\.MZK01-(\\d{9})$"
      },
      {
        "base": "MZK03",
        "id_template": "mzk.MZK03-{system_number}",
        "pattern": "^mzk\\.MZK03-(\\d{9})$"
      },
      {
        "base": "SKC",
        "id_template": "caslin.SKC01-{system_number}",
        "pattern": "^caslin\\.SKC01-(\\d{9})$",
        "is_target": true
      }
    ]
  }
}
EOF
)

http --session=demo-admin POST "$APP_URL/settings/record-tools/authority-linkers" \
  Content-Type:application/json \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 3. Set Validation settings
###############################################################################
print_step "Setting Validation settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "kramerius-links": {
    "kramerius_host": "https://api.kramerius.mzk.cz/search",
    "kramerius_client_url": "https://www.digitalniknihovna.cz/mzk/uuid/{pid}",
    "solr_cloud": true,
    "search_page_size": 10
  }
}
EOF
)

http --session=demo-admin POST "$APP_URL/settings/record-tools/validators" \
    Content-Type:application/json \
    <<< "$SETTINGS_JSON"

pause

###############################################################################
# 4. Run authority linking
###############################################################################
print_step "Run authority linking task"

AUTHORITY_LINKING_TASK_JSON=$(cat <<'EOF'
{
  "linkers": ["knihovny-cz"],
  "target_base": "SKC",
  "filters": {}
}
EOF
)

http --session=demo-admin POST "$APP_URL/authority-linking/task" \
    Content-Type:application/json \
    <<< "$AUTHORITY_LINKING_TASK_JSON"

wait_for_tasks
echo "Authority linking task completed."
echo

pause

###############################################################################
# 5. Run comparison task
###############################################################################
print_step "Run comparison task"

COMPARISON_TASK_JSON=$(cat <<'EOF'
{
  "target_base": "SKC",
  "filters": {}
}
EOF
)

http --session=demo-admin POST "$APP_URL/comparison/task" \
    Content-Type:application/json \
    <<< "$COMPARISON_TASK_JSON"

wait_for_tasks
echo "Comparison task completed."
echo

pause

###############################################################################
# 6. Run validation task
###############################################################################
print_step "Run validation task"

VALIDATION_TASK_JSON=$(cat <<'EOF'
{
  "validators": ["kramerius-links"],
  "filters": {}
}
EOF
)

http --session=demo-admin POST "$APP_URL/validation/task" \
    Content-Type:application/json \
    <<< "$VALIDATION_TASK_JSON"

wait_for_tasks
echo "Validation task completed."
echo

###############################################################################
# 7. Search records
###############################################################################
print_step "Searching for catalog records"

http --session=demo-admin POST "$APP_URL/catalog-records/search" \
    Content-Type:application/json \
    <<< '{"filters": {"bases": ["MZK01"]}, "page": 1, "page_size": 5}'

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
