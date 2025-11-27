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

# Elasticsearch query for active tasks
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
        "pattern": "^caslin\\.SKC01-(\\d{9})$"
      }
    ]
  }
}
EOF
)

http POST "$APP_URL/settings/record-tools/authority-linkers" \
  Content-Type:application/json \
  "Authorization: Bearer $ADMIN_TOKEN" \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 3. Set Comparison settings
###############################################################################
print_step "Setting Comparison settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "rule-based": {
    "rules": [
      {
        "tag": "20",
        "subfields": ["a"],
        "rule_scores": {}
      },
      {
        "tag": "100",
        "subfields": ["a", "b", "c"],
        "rule_scores": {}
      },
      {
        "tag": "245",
        "subfields": ["a", "b", "c"],
        "rule_scores": {}
      },
      {
        "tag": "650",
        "subfields": ["a", "2", "7"],
        "rule_scores": {}
      }
    ]
  }
}
EOF
)

http POST "$APP_URL/settings/record-tools/comparators" \
    Content-Type:application/json \
    "Authorization: Bearer $ADMIN_TOKEN" \
    <<< "$SETTINGS_JSON"

pause

###############################################################################
# 4. Set Validation settings
###############################################################################
print_step "Setting Validation settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "kramerius-links": {
    "url_to_pid_pattern": "https?://[^/]+/mzk/uuid/(uuid:[0-9a-fA-F-]+)",
    "link_text_pattern": "Digitalizovaný dokument",
    "kramerius_host": "https://api.kramerius.mzk.cz/search"
  }
}
EOF
)

http POST "$APP_URL/settings/record-tools/validators" \
    Content-Type:application/json \
    "Authorization: Bearer $ADMIN_TOKEN" \
    <<< "$SETTINGS_JSON"

pause

###############################################################################
# 5. Run authority linking
###############################################################################
print_step "Run authority linking task"

AUTHORITY_LINKING_TASK_JSON=$(cat <<'EOF'
{
  "linkers": [
    "knihovny-cz"
  ],
  "target_base": "SKC",
  "query": {
    "query": {
      "match_all": {}
    }
  }
}
EOF
)

http POST "$APP_URL/authority-linking/task" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    Content-Type:application/json \
    <<< "$AUTHORITY_LINKING_TASK_JSON"

sleep 5

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

echo "Authority linking task completed."
echo

pause

###############################################################################
# 6. Run comparison task
###############################################################################
print_step "Run comparison task"

COMPARISON_TASK_JSON=$(cat <<'EOF'
{
  "comparator": "intiim",
  "target_base": "SKC",
  "query": {
    "query": {
      "match_all": {}
    }
  }
}
EOF
)

http POST "$APP_URL/comparison/task" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    Content-Type:application/json \
    <<< "$COMPARISON_TASK_JSON"

sleep 5

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

echo "Comparison task completed."
echo

pause

###############################################################################
# 7. Run validation task
###############################################################################
print_step "Run validation task"

VALIDATION_TASK_JSON=$(cat <<'EOF'
{
  "validators": ["kramerius-links"],
  "query": {
    "query": {
      "match_all": {}
    }
  }
}
EOF
)

http POST "$APP_URL/validation/task" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    Content-Type:application/json \
    <<< "$VALIDATION_TASK_JSON"

sleep 5

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

echo "Validation task completed."
echo

###############################################################################
# 8. Run hide record task on one record
###############################################################################
print_step "Hiding one catalog record"

HIDE_RECORD_TASK_JSON=$(cat <<'EOF'
{
  "query": {
    "query": {
      "term": {
        "system_number": "001818019"
      }
    }
  }
}
EOF
)

http POST "$APP_URL/catalog-records/visibility" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    Content-Type:application/json \
    <<< "$HIDE_RECORD_TASK_JSON"
  
sleep 5

RECORD_QUERY_JSON=$(cat <<'EOF'
{
  "query": {
    "term": {
      "system_number": "001818019"
    }
  }
}
EOF
)

http POST "$APP_URL/catalog-records/search" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    Content-Type:application/json \
    <<< "$RECORD_QUERY_JSON"

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
