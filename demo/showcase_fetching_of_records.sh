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
# 2. Set Catalog app settings
###############################################################################
print_step "Setting Catalog app settings"

SETTINGS_JSON=$(cat <<'EOF'
{
  "clients": [
    {
      "host": "https://aleph.mzk.cz",
      "endpoint": "OAI",
      "base": "MZK01",
      "system_number_pattern": "\\d{9}",
      "oai_sets": ["MZK01-VDK"],
      "oai_identifier_template": "oai:aleph.mzk.cz:{base}-{doc_number}"
    }
  ]
}
EOF
)

http --session=demo-admin POST "$APP_URL/settings/system/catalog" \
  Content-Type:application/json \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 3. Fetch 1 catalog record
###############################################################################
print_step "Fetching 1 catalog record from Aleph"

http --ignore-stdin --session=demo-admin POST "$APP_URL/catalog-records/fetch" \
    base="MZK01" \
    system_number="001818019"

pause

###############################################################################
# 4. Fetch 100 catalog records in batch
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

http --session=demo-admin POST "$APP_URL/catalog-records/fetch-batch" \
    Content-Type:application/json \
    <<< "$RECORDS_BATCH_JSON"

pause

###############################################################################
# 5. Sync with Aleph to get records modified in the last day
###############################################################################
print_step "Syncing catalog records modified in the last day from Aleph"

SYNC_JSON=$(jq -n \
    --arg base "MZK01" \
    --arg from_date "$(date -d '1 days ago' +%Y-%m-%d)" \
    '{base: $base, from_date: $from_date}')

http --session=demo-admin POST "$APP_URL/catalog-records/sync" \
    Content-Type:application/json \
    <<< "$SYNC_JSON"

pause

###############################################################################
# 6. Wait for all background tasks to complete
###############################################################################
print_step "Waiting for all background tasks to complete"

while true; do
    response=$(http --session=demo-admin --print=b POST "$APP_URL/tasks/search-own" \
        Content-Type:application/json \
        <<< '{"filters": {"status": ["Pending", "Started"]}}')

    count=$(echo "$response" | jq '.total')
    echo "Tasks still pending/running: $count. Checking every 30 seconds..."

    if [ "$count" -eq 0 ]; then
        break
    fi

    sleep 30
done

echo "All background tasks completed."
echo

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
