#!/bin/bash
# One-time fix: update frontend deploy script to clean before pull
# This runs on the server via deploy-backend.sh context

cat > /opt/eifavpn/scripts/deploy-frontend.sh << 'ENDSCRIPT'
#!/bin/bash
set -e
cd /opt/eifavpn/prod/frontend

echo "=== Cleaning untracked files ==="
git clean -fd
git checkout .
echo "=== Pulling latest frontend ==="
git pull origin main
echo "=== Installing dependencies ==="
npm ci --production=false 2>&1 | tail -3
echo "=== Building ==="
npm run build
echo "=== Frontend deployed successfully ==="
ENDSCRIPT

chmod +x /opt/eifavpn/scripts/deploy-frontend.sh
echo "Frontend deploy script updated!"

# Now also deploy frontend
/opt/eifavpn/scripts/deploy-frontend.sh
