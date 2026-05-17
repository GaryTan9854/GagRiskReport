#!/bin/bash
set -e

REMOTE_USER="gary"
REMOTE_HOST="192.168.1.11"
REMOTE_DIR="/Users/gary/gagrisk-dist"
PORT=3010
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_OPTS="-i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"
QUICK=false

for arg in "$@"; do
  [[ "$arg" == "--quick" ]] && QUICK=true
done

cd "$(dirname "$0")"

# ── Version bump ───────────────────────────────────────────────────────────────
CURRENT_VER=$(python3 -c "
import re
with open('backend/main.py') as f:
    m = re.search(r'APP_VERSION = \"([^\"]+)\"', f.read())
    print(m.group(1) if m else '1.0')
")
NEXT_VER=$(python3 -c "
parts = '$CURRENT_VER'.split('.')
major, minor = int(parts[0]), int(parts[1])
print(f'{major + 1}.0' if minor == 20 else f'{major}.{minor + 1}')
")
python3 -c "
import re
path = 'backend/main.py'
with open(path) as f:
    content = f.read()
content = re.sub(r'APP_VERSION = \"[^\"]+\"', 'APP_VERSION = \"$NEXT_VER\"', content)
with open(path, 'w') as f:
    f.write(content)
"
echo "🔢 Version bumped: v$CURRENT_VER → v$NEXT_VER"

echo "📝 [0/4] Committing to git…"
git add -A
if ! git diff --cached --quiet; then
  git commit -m "deploy GagRiskReport v$NEXT_VER $(date '+%Y-%m-%d %H:%M')"
fi
if git remote | grep -q origin; then
  git push origin main 2>/dev/null || git push origin master 2>/dev/null || echo "   (git push skipped)"
fi

echo "💾 [1/4] Backing up DB on MBP…"
ssh $SSH_OPTS $REMOTE_USER@$REMOTE_HOST "
  DB=\$HOME/db/gagrisk/gag_risk.db
  BACKUP_DIR=\$HOME/db-backups/gagrisk
  mkdir -p \$BACKUP_DIR
  if [ -f \$DB ]; then
    STAMP=\$(date +%Y%m%d_%H%M%S)
    cp \$DB \$BACKUP_DIR/gag_risk_\$STAMP.db
    ls -t \$BACKUP_DIR/gag_risk_*.db 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
    echo \"   DB backed up\"
  fi
"

echo "📦 [2/4] Syncing source to MBP…"
rsync -az -e "ssh $SSH_OPTS" \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'gag_risk.db' \
  --exclude 'venv/' \
  --exclude 'node_modules/' \
  --exclude 'dist/' \
  --exclude 'backend/static/' \
  --exclude '.git/' \
  --exclude '*.pdf' \
  --exclude '*.xls' \
  --exclude '*.xlsx' \
  "$(dirname "$0")/" \
  $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

echo "🔨 [3/4] Building frontend on MBP…"
ssh $SSH_OPTS $REMOTE_USER@$REMOTE_HOST "
  zsh -lic '
  cd $REMOTE_DIR/frontend
  if [ \"$QUICK\" = false ]; then
    echo \"   → npm install…\"
    npm install --silent
  fi
  echo \"   → vite build…\"
  npm run build
  '"

echo "🚀 [4/4] Installing deps + restarting PM2…"
ssh $SSH_OPTS $REMOTE_USER@$REMOTE_HOST "
  zsh -lic '
  cd $REMOTE_DIR/backend
  mkdir -p \$HOME/db/gagrisk
  if [ ! -d venv ]; then
    python3 -m venv venv
  fi
  if [ \"$QUICK\" = false ]; then
    venv/bin/pip install -r requirements.txt -q
  fi
  # Seed DB if empty
  if [ ! -f \$HOME/db/gagrisk/gag_risk.db ]; then
    DB_PATH=\$HOME/db/gagrisk/gag_risk.db venv/bin/python seed_data.py
  fi
  pm2 restart gagrisk 2>/dev/null || \
    pm2 start venv/bin/python3 \
      --name gagrisk \
      --cwd $REMOTE_DIR/backend \
      -- -m uvicorn main:app --host 0.0.0.0 --port 3010 --no-access-log
  pm2 save --force
  '
"

echo "🔄 [5/5] Pulling DB backup MBP → MBA…"
LOCAL_BACKUP="$HOME/Documents/.db-backups/gagriskreport"
mkdir -p "$LOCAL_BACKUP"
rsync -az -e "ssh $SSH_OPTS" \
  $REMOTE_USER@$REMOTE_HOST:/Users/gary/db/gagrisk/ \
  "$LOCAL_BACKUP/"
echo "   DB synced to $LOCAL_BACKUP/"

echo ""
echo "✅ Deploy complete → GagRiskReport v$NEXT_VER → https://gaglobal.visadelab.xyz"
