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
# 2. Set Catalog app settings
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
# 3. Verify settings
###############################################################################
print_step "Fetching current Catalog settings"

http GET "$APP_URL/settings/app/Catalog" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 4. Get schema for Catalog settings
###############################################################################
print_step "Fetching Catalog settings schema"

http GET "$APP_URL/settings/app/Catalog/schema" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 5. Set Authority Linking settings
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

http POST "$APP_URL/settings/tasks/AuthorityLinking" \
  Content-Type:application/json \
  "Authorization: Bearer $ADMIN_TOKEN" \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 6. Verify settings
###############################################################################

http GET "$APP_URL/settings/tasks/AuthorityLinking" "Authorization: Bearer $ADMIN_TOKEN"

pause

###############################################################################
# 7. Get schema for AuthorityLinking settings
###############################################################################

http GET "$APP_URL/settings/tasks/AuthorityLinking/schema" "Authorization: Bearer $ADMIN_TOKEN"

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
