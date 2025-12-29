#!/bin/bash
# Script to verify Prometheus can scrape bot metrics

echo "=== Verifying Prometheus Setup ==="
echo ""

# Check if bot metrics endpoint is accessible
echo "1. Checking bot metrics endpoint (localhost:8000/metrics)..."
if curl -s -f http://localhost:8000/metrics > /dev/null 2>&1; then
    echo "   ✓ Bot metrics endpoint is accessible"
    METRIC_COUNT=$(curl -s http://localhost:8000/metrics | grep -c "^ds_bot_" || echo "0")
    echo "   Found $METRIC_COUNT ds_bot_ metrics"
else
    echo "   ✗ Bot metrics endpoint is NOT accessible"
    echo "   Make sure the bot is running with metrics enabled"
    exit 1
fi

echo ""

# Check if Prometheus is running
echo "2. Checking Prometheus (localhost:9090)..."
if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "   ✓ Prometheus is running"
else
    echo "   ✗ Prometheus is NOT running"
    echo "   Start it with: docker-compose up -d prometheus"
    exit 1
fi

echo ""

# Check Prometheus targets
echo "3. Checking Prometheus targets..."
TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null)
if [ $? -eq 0 ]; then
    HEALTH=$(echo "$TARGETS" | grep -o '"health":"[^"]*"' | head -1 | cut -d'"' -f4)
    if [ "$HEALTH" = "up" ]; then
        echo "   ✓ Bot target is UP"
    else
        echo "   ✗ Bot target is DOWN"
        LAST_ERROR=$(echo "$TARGETS" | grep -o '"lastError":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo "   Last error: $LAST_ERROR"
        echo ""
        echo "   Troubleshooting:"
        echo "   - Make sure the bot is running on localhost:8000"
        echo "   - Check Prometheus logs: docker-compose logs prometheus"
        echo "   - Verify Prometheus config: docker-compose exec prometheus cat /etc/prometheus/prometheus.yml"
    fi
else
    echo "   ✗ Could not query Prometheus API"
fi

echo ""

# Check if metrics are being scraped
echo "4. Checking if metrics are being scraped..."
METRICS=$(curl -s "http://localhost:9090/api/v1/query?query=ds_bot_uptime_seconds" 2>/dev/null)
if echo "$METRICS" | grep -q '"result":\[\]'; then
    echo "   ✗ No metrics found in Prometheus"
    echo "   Prometheus may not be scraping yet, or the bot just started"
else
    echo "   ✓ Metrics found in Prometheus"
    UPTIME=$(echo "$METRICS" | grep -o '"value":\[[^]]*\]' | head -1 | cut -d',' -f2 | tr -d ']')
    if [ -n "$UPTIME" ]; then
        echo "   Bot uptime: $UPTIME seconds"
    fi
fi

echo ""
echo "=== Verification Complete ==="

