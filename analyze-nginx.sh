#!/bin/bash
# One-time nginx log analysis script
# Run via Jenkins pipeline (has sudo access)

echo "=== NGINX LOG LOCATIONS ==="
find /var/log/ -name "*nginx*" -o -name "*access*" -o -name "*error*" 2>/dev/null | grep -i nginx | head -20
ls -lah /var/log/nginx/ 2>/dev/null

echo ""
echo "=== NGINX CONFIG ==="
ls -la /etc/nginx/sites-enabled/ 2>/dev/null
echo ""

echo "=== NGINX ERROR LOG (last 3 days) ==="
if [ -f /var/log/nginx/error.log ]; then
    # Filter last 3 days of errors
    awk -v d="$(date -d '3 days ago' '+%Y/%m/%d')" '$0 >= d' /var/log/nginx/error.log 2>/dev/null | tail -200
else
    echo "No error.log found at /var/log/nginx/error.log"
    # Try other locations
    for f in /var/log/nginx/*.log /var/log/nginx/*.log.1; do
        if [ -f "$f" ]; then
            echo "--- Found: $f ($(wc -l < "$f") lines) ---"
            tail -5 "$f"
            echo ""
        fi
    done
fi

echo ""
echo "=== NGINX ACCESS LOG - 4xx/5xx errors (last 3 days) ==="
if [ -f /var/log/nginx/access.log ]; then
    # Count error responses
    echo "Status code distribution (last 1000 lines):"
    tail -1000 /var/log/nginx/access.log | awk '{print $9}' | sort | uniq -c | sort -rn | head -20
    echo ""
    echo "5xx errors:"
    tail -5000 /var/log/nginx/access.log | awk '$9 >= 500 {print}' | tail -30
    echo ""
    echo "404 errors (top paths):"
    tail -5000 /var/log/nginx/access.log | awk '$9 == 404 {print $7}' | sort | uniq -c | sort -rn | head -20
else
    echo "No access.log at default path"
fi

echo ""
echo "=== GUNICORN/APP LOGS ==="
journalctl -u eifavpn-prod --since "3 days ago" --no-pager -n 100 2>/dev/null | tail -50

echo ""
echo "=== SYSTEMD SERVICE STATUS ==="
systemctl status eifavpn-prod --no-pager 2>/dev/null | head -15
systemctl status nginx --no-pager 2>/dev/null | head -15

echo ""
echo "=== NGINX CONFIG TEST ==="
nginx -t 2>&1
