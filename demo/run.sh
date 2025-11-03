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

# Test user credentials
TEST_EMAIL="test@mzk.cz"
TEST_FIRSTNAME="Test"
TEST_LASTNAME="User"
TEST_PASSWORD="TestPassword"

# Admin credentials
ADMIN_EMAIL="admin@mzk.cz"
ADMIN_PASSWORD="AdminPassword"

###############################################################################
# 1. Register new user
###############################################################################
print_step "Registering test user"
echo "Registration can fail if the user already exists, which is fine."
echo

http POST "$APP_URL/auth/register" \
    email="$TEST_EMAIL" \
    first_name="$TEST_FIRSTNAME" \
    last_name="$TEST_LASTNAME" \
    password="$TEST_PASSWORD"

pause

###############################################################################
# 2. Login as test user
###############################################################################
print_step "Logging in as test user"

http --form POST "$APP_URL/auth/token" \
    username="$TEST_EMAIL" \
    password="$TEST_PASSWORD"

TEST_TOKEN=$(http --form --print=b POST "$APP_URL/auth/token" \
    username="$TEST_EMAIL" \
    password="$TEST_PASSWORD" | jq -r .access_token)

pause

###############################################################################
# 3. Get current test user info
###############################################################################
print_step "Fetching /auth/me for test user"

http GET "$APP_URL/auth/me" "Authorization: Bearer $TEST_TOKEN"

TEST_USER_ID=$(http GET "$APP_URL/auth/me" \
    "Authorization: Bearer $TEST_TOKEN" | jq -r '.id')

pause

###############################################################################
# 4. Login as admin
###############################################################################
print_step "Logging in as admin"

http --form POST "$APP_URL/auth/token" \
    username="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD"

ADMIN_TOKEN=$(http --form --print=b POST "$APP_URL/auth/token" \
    username="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD" | jq -r .access_token)

pause

###############################################################################
# 5. Get current admin info
###############################################################################
print_step "Fetching /auth/me for admin"

http GET "$APP_URL/auth/me" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 6. Display all roles
###############################################################################
print_step "Fetching all roles"

http GET "$APP_URL/access-control/roles" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 7. Create new role
###############################################################################
print_step "Creating new role"

http POST "$APP_URL/access-control/roles" \
    "Authorization:Bearer $ADMIN_TOKEN" \
    Content-Type:application/json \
    name="DemoRole" \
    permissions:='["ReadRecords"]'

ROLE_ID=$(http GET "$APP_URL/access-control/roles" \
    "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.items[-1].id')

pause

###############################################################################
# 8. Update new role
###############################################################################
print_step "Updating role $ROLE_ID"

http PUT "$APP_URL/access-control/roles/$ROLE_ID" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    name="DemoRoleUpdated" \
    permissions:='["ReadRecords"]'

pause

###############################################################################
# 9. List all users
###############################################################################
print_step "Fetching all users"

http GET "$APP_URL/access-control/users" \
    "Authorization: Bearer $ADMIN_TOKEN" 

pause

###############################################################################
# 10. Filter users by email
###############################################################################
print_step "Fetching users filtered by email (test*)"

http GET "$APP_URL/access-control/users" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    email="test"

pause

###############################################################################
# 11. Assign new role to test user
###############################################################################
print_step "Assigning new role $ROLE_ID to user $TEST_USER_ID"

http PATCH "$APP_URL/access-control/users/$TEST_USER_ID/assign-role/$ROLE_ID" \
  "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 12. Get current test user info
###############################################################################
print_step "Fetching /auth/me for test user"

http GET "$APP_URL/auth/me" "Authorization: Bearer $TEST_TOKEN"

pause

###############################################################################
# 13. Unassign new role from test user
###############################################################################
print_step "Unassigning new role $ROLE_ID from user $TEST_USER_ID"

http PATCH "$APP_URL/access-control/users/$TEST_USER_ID/unassign-role/$ROLE_ID" \
  "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 14. Get current test user info
###############################################################################
print_step "Fetching /auth/me for test user"

http GET "$APP_URL/auth/me" "Authorization: Bearer $TEST_TOKEN"

pause

###############################################################################
# 15. Delete new role
###############################################################################
print_step "Deleting role $ROLE_ID"

http DELETE "$APP_URL/access-control/roles/$ROLE_ID" \
    "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 16. Set Catalog app settings
###############################################################################
print_step "Setting Catalog app settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "clients": [
    {
      "base": "MZK01",
      "oai": {
        "host": "https://aleph.mzk.cz",
        "endpoint": "OAI",
        "timeout": 30,
        "total_retry": 5,
        "retry_backoff_factor": 1,
        "base": "MZK01",
        "system_number_pattern": "\\d{9}",
        "oai_sets": ["MZK01-VDK"],
        "oai_identifier_template": "oai:aleph.mzk.cz:{base}-{doc_number}"
      }
    }
  ]
}
EOF
)

http POST "$APP_URL/settings/app/Catalog" \
  Content-Type:application/json \
  "Authorization: Bearer $ADMIN_TOKEN" \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 17. Verify settings
###############################################################################
print_step "Fetching current Catalog settings"

http GET "$APP_URL/settings/app/Catalog" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 18. Get schema for Catalog settings
###############################################################################
print_step "Fetching Catalog settings schema"

http GET "$APP_URL/settings/app/Catalog/schema" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 19. Set Authority Linking settings
###############################################################################
print_step "Setting Authority Linking settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "knihovny-cz": {
    "api_url": "https://api.knihovny.cz/v1/",
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

http POST "$APP_URL/settings/tasks/AuthorityLinking" \
  Content-Type:application/json \
  "Authorization: Bearer $ADMIN_TOKEN" \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 20. Verify settings
###############################################################################

http GET "$APP_URL/settings/tasks/AuthorityLinking" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 21. Get schema for AuthorityLinking settings
###############################################################################

http GET "$APP_URL/settings/tasks/AuthorityLinking/schema" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 22. Set Comparison settings
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

http POST "$APP_URL/settings/tasks/Comparison" \
    Content-Type:application/json \
    "Authorization: Bearer $ADMIN_TOKEN" \
    <<< "$SETTINGS_JSON"

pause

###############################################################################
# 23. Set Validation settings
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

http POST "$APP_URL/settings/tasks/Validation" \
    Content-Type:application/json \
    "Authorization: Bearer $ADMIN_TOKEN" \
    <<< "$SETTINGS_JSON"

pause

###############################################################################
# 24. Fetch 1 catalog record
###############################################################################
print_step "Fetching 1 catalog record from Aleph"

http POST "$APP_URL/catalog-records/fetch" \
    "Authorization: Bearer $ADMIN_TOKEN" \
    base="MZK01" \
    system_number="001818019"
  
pause

###############################################################################
# 25. Fetch 100 catalog records in batch
###############################################################################
print_step "Fetching 100 catalog records from Aleph"

RECORDS_BATCH_JSON=$(cat <<'EOF'
{
  "per_base": [
    {
      "base": "MZK01",
      "system_numbers": [
        "001818019",
        "001618553",
        "001778730",
        "001617541",
        "001920620",
        "001868590",
        "001587746",
        "001663416",
        "001683473",
        "001777427",
        "001776536",
        "001791709",
        "001561756",
        "001637116",
        "001662935",
        "001726233",
        "001801519",
        "001822952",
        "001619012",
        "001823292",
        "001691810",
        "001815195",
        "001840399",
        "000720847",
        "001914511",
        "001798870",
        "001678458",
        "001919777",
        "001676202",
        "001861959",
        "001786349",
        "001875706",
        "001755670",
        "001866002",
        "001921033",
        "001873177",
        "001584272",
        "001779168",
        "001918881",
        "001790687",
        "001806533",
        "001672659",
        "001780996",
        "001760091",
        "001781190",
        "001800221",
        "001724808",
        "001661186",
        "001697959",
        "001707319",
        "001807683",
        "001777342",
        "001813989",
        "001919954",
        "001767568",
        "001775028",
        "001671317",
        "001831834",
        "001628890",
        "001615130",
        "001868849",
        "001815150",
        "001647080",
        "001573329",
        "001779001",
        "001698286",
        "001795669",
        "001587385",
        "001708214",
        "001529993",
        "001731177",
        "001838096",
        "001755599",
        "001775196",
        "001774641",
        "001602152",
        "001587428",
        "001906026",
        "001663446",
        "001637490",
        "001800846",
        "001673404",
        "001795917",
        "001673406",
        "001588003",
        "001558478",
        "001690486",
        "001758889",
        "001603363",
        "001561477",
        "001562497",
        "001775117",
        "001873176",
        "001919506",
        "001729170",
        "001572245",
        "001793986",
        "001800995",
        "001651106",
        "001676741"
      ]
    }
  ]
}
EOF
)

http POST "$APP_URL/catalog-records/fetch-batch" \
    Content-Type:application/json \
    "Authorization: Bearer $ADMIN_TOKEN" \
    <<< "$RECORDS_BATCH_JSON"
  
pause

###############################################################################
# 25. Sync with Aleph to get records modified in the last 14 days
###############################################################################
print_step "Syncing catalog records modified in the last 14 days from Aleph"

SYNC_JSON=$(jq -n \
    --arg base "MZK01" \
    --arg from_date "$(date -d '7 days ago' +%Y-%m-%d)" \
    '{base: $base, from_date: $from_date}')

http POST "$APP_URL/catalog-records/sync" \
    Content-Type:application/json \
    "Authorization: Bearer $ADMIN_TOKEN" \
    <<< "$SYNC_JSON"

pause

###############################################################################
# 26. Wait for all background tasks to complete
###############################################################################
print_step "Waiting for all background tasks to complete"

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
    echo "Tasks still pending/running: $count. Checking every 30 seconds..."

    if [ "$count" -eq 0 ]; then
        break
    fi

    sleep 30
done

echo "All background tasks completed."
echo

pause

###############################################################################
# 27. Recreate indexes
###############################################################################
print_step "Run recreating of indexes"

http POST "$APP_URL/system/recreate-indexes" \
    "Authorization: Bearer $ADMIN_TOKEN"

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

echo "Recreating of indexes completed."
echo

pause

###############################################################################
# 28. Run authority linking
###############################################################################
print_step "Run authority linking task"

AUTHORITY_LINKING_TASK_JSON=$(cat <<'EOF'
{
  "linkers": [
    "knihovny-cz"
  ],
  "target_base": "SKC",
  "query": {
    "match_all": {}
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
# 29. Run comparison task
###############################################################################
print_step "Run comparison task"

COMPARISON_TASK_JSON=$(cat <<'EOF'
{
  "comparator": "rule-based",
  "target-base": "SKC",
  "query": {
    "match_all": {}
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
# 30. Run validation task
###############################################################################
print_step "Run validation task"

VALIDATION_TASK_JSON=$(cat <<'EOF'
{
  "validators": ["kramerius-links"],
  "query": {
    "match_all": {}
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

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"