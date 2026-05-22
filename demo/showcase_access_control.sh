#!/bin/bash
set -euo pipefail

APP_URL="http://localhost:8000"

# httpie sessions (cookies are persisted per session)
TEST_SESSION="demo-test-user"
ADMIN_SESSION="demo-admin"

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

http POST "$APP_URL/auth/sign-up" \
    email="$TEST_EMAIL" \
    first_name="$TEST_FIRSTNAME" \
    last_name="$TEST_LASTNAME" \
    password="$TEST_PASSWORD"

pause

###############################################################################
# 2. Login as test user (cookie-based auth)
###############################################################################
print_step "Logging in as test user"

http --session="$TEST_SESSION" POST "$APP_URL/auth/login" \
    email="$TEST_EMAIL" \
    password="$TEST_PASSWORD"

pause

###############################################################################
# 3. Get current test user info
###############################################################################
print_step "Fetching /auth/me for test user"

http --session="$TEST_SESSION" GET "$APP_URL/auth/me"

TEST_USER_ID=$(http --session="$TEST_SESSION" --print=b GET "$APP_URL/auth/me" \
    | jq -r '.id')

pause

###############################################################################
# 4. Login as admin (cookie-based auth)
###############################################################################
print_step "Logging in as admin"

http --session="$ADMIN_SESSION" POST "$APP_URL/auth/login" \
    email="$ADMIN_EMAIL" \
    password="$ADMIN_PASSWORD"

pause

###############################################################################
# 5. Get current admin info
###############################################################################
print_step "Fetching /auth/me for admin"

http --session="$ADMIN_SESSION" GET "$APP_URL/auth/me"

pause

###############################################################################
# 6. Display all roles
###############################################################################
print_step "Fetching all roles"

http --session="$ADMIN_SESSION" GET "$APP_URL/access-control/roles"

pause

###############################################################################
# 7. Create new role
###############################################################################
print_step "Creating new role"

http --session="$ADMIN_SESSION" POST "$APP_URL/access-control/roles" \
    name="DemoRole" \
    permissions:='["ReadRecords"]'

ROLE_ID=$(http --session="$ADMIN_SESSION" --print=b GET "$APP_URL/access-control/roles" \
    | jq -r '.items[-1].id')

pause

###############################################################################
# 8. Update new role
###############################################################################
print_step "Updating role $ROLE_ID"

http --session="$ADMIN_SESSION" PUT "$APP_URL/access-control/roles/$ROLE_ID" \
    name="DemoRoleUpdated" \
    permissions:='["ReadRecords"]'

pause

###############################################################################
# 9. List all users
###############################################################################
print_step "Fetching all users"

http --session="$ADMIN_SESSION" GET "$APP_URL/access-control/users"

pause

###############################################################################
# 10. Filter users by email
###############################################################################
print_step "Fetching users filtered by email (test*)"

http --session="$ADMIN_SESSION" GET "$APP_URL/access-control/users?email=test"

pause

###############################################################################
# 11. Assign new role to test user
###############################################################################
print_step "Assigning new role $ROLE_ID to user $TEST_USER_ID"

http --session="$ADMIN_SESSION" PATCH \
    "$APP_URL/access-control/users/$TEST_USER_ID/assign-role/$ROLE_ID"

pause

###############################################################################
# 12. Get current test user info
###############################################################################
print_step "Fetching /auth/me for test user"

http --session="$TEST_SESSION" GET "$APP_URL/auth/me"

pause

###############################################################################
# 13. Unassign new role from test user
###############################################################################
print_step "Unassigning new role $ROLE_ID from user $TEST_USER_ID"

http --session="$ADMIN_SESSION" PATCH \
    "$APP_URL/access-control/users/$TEST_USER_ID/unassign-role/$ROLE_ID"

pause

###############################################################################
# 14. Get current test user info
###############################################################################
print_step "Fetching /auth/me for test user"

http --session="$TEST_SESSION" GET "$APP_URL/auth/me"

pause

###############################################################################
# 15. Delete new role
###############################################################################
print_step "Deleting role $ROLE_ID"

http --session="$ADMIN_SESSION" DELETE "$APP_URL/access-control/roles/$ROLE_ID"

echo -e "\n${CYAN}=== Demo completed successfully! ===${NC}\n"
