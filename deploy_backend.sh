#!/bin/bash
# ==============================================================================
# SLOPARA BACKEND SAFE DEPLOYMENT SCRIPT (DOCKER)
# ==============================================================================
# Fail immediately on any critical pipeline error
set -e

# --- CONFIGURATION ---
PROJECT_DIR="/root/suropara/slopara-backenddjango"
CONTAINER_NAME="backend"
DB_CONTAINER="db"

# --- COLORS ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}[1/6] Navigating to backend directory: ${PROJECT_DIR}...${NC}"
cd "$PROJECT_DIR" || { echo -e "${RED}Directory not found!${NC}"; exit 1; }

echo -e "${BLUE}[2/6] Securing local data and forcing repository sync...${NC}"
cp .env /tmp/.env.bak 2>/dev/null || true
cp deploy_backend.sh /tmp/deploy_backend.sh.bak 2>/dev/null || true

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Strict Git Pull (Aborts merges, forces main branch tracking)
git merge --abort 2>/dev/null || true
git fetch --all
git reset --hard origin/main
git pull origin main

mv /tmp/.env.bak .env 2>/dev/null || true
mv /tmp/deploy_backend.sh.bak deploy_backend.sh 2>/dev/null || true
chmod +x deploy_backend.sh

echo -e "${BLUE}[3/6] Rebuilding Docker infrastructure...${NC}"
docker-compose up -d --build

echo -e "${BLUE}[4/6] Taking care of Database & Assets (Backup, Migrate, Static)...${NC}"
# Extract a quick SQL dump of the PostgreSQL database inside the container before applying risky migrations
docker-compose exec -T $DB_CONTAINER pg_dump -U slopara_user slopara > /tmp/slopara_db_backup_$(date +%F_%H%M).sql || echo -e "${RED}Warning: DB Backup Skipped/Failed${NC}"

docker-compose exec -T $CONTAINER_NAME python manage.py migrate
docker-compose exec -T $CONTAINER_NAME python manage.py collectstatic --noinput
docker-compose exec -T $CONTAINER_NAME python manage.py generate_svgs

echo -e "${BLUE}[5/6] Restarting backend container to strictly apply changes...${NC}"
docker-compose restart $CONTAINER_NAME

echo -e "${BLUE}[6/6] Pruning dangling images to prevent disk exhaustion...${NC}"
docker image prune -f

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN} SUCCESS: Backend deployment complete!     ${NC}"
echo -e "${GREEN} Daphne ASGI and Static Assets are ready.  ${NC}"
echo -e "${GREEN}===========================================${NC}"

docker-compose logs --tail 15 $CONTAINER_NAME