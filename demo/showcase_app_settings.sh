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
# 3. Verify settings
###############################################################################
print_step "Fetching current Catalog settings"

http --session=demo-admin GET "$APP_URL/settings/system/catalog"

pause

###############################################################################
# 4. Set Authority Linking settings
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

http --session=demo-admin POST "$APP_URL/settings/record-tools/authority-linkers" \
  Content-Type:application/json \
  <<< "$SETTINGS_JSON"

pause

###############################################################################
# 5. Verify settings
###############################################################################

http --session=demo-admin GET "$APP_URL/settings/record-tools/authority-linkers"

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
