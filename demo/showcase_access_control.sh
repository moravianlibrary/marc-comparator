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

http --form POST "$APP_URL/auth/login" \
    username="$TEST_EMAIL" \
    password="$TEST_PASSWORD"

TEST_TOKEN=$(http --form --print=b POST "$APP_URL/auth/login" \
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

http --form POST "$APP_URL/auth/login" \
    username="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD"

ADMIN_TOKEN=$(http --form --print=b POST "$APP_URL/auth/login" \
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

http GET "$APP_URL/access-control/users?email=test" \
    "Authorization: Bearer $ADMIN_TOKEN"

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

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
