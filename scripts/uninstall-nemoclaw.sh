#!/bin/bash

echo "========================================================="
echo "        NemoClaw Complete Uninstall Script"
echo "========================================================="
echo ""

# 1. Stop all NemoClaw/OpenShell processes
echo "[1/10] Stopping NemoClaw processes..."
pkill -f "nemoclaw" 2>/dev/null || true
pkill -f "openshell" 2>/dev/null || true
pkill -f "ssh-proxy.*gateway" 2>/dev/null || true
pkill -f "openclaw-gateway" 2>/dev/null || true
sleep 2
echo "  OK Processes stopped"

# 2. Destroy sandbox (if nemoclaw CLI exists)
echo "[2/10] Destroying sandbox..."
if command -v nemoclaw &>/dev/null; then
  cd /Users/mck/Desktop/NemoClaw 2>/dev/null || true
  nemoclaw my-assistant destroy --yes 2>/dev/null || echo "  Sandbox destroy attempted"
else
  echo "  nemoclaw CLI not found - skipping"
fi
echo "  OK Sandbox destroyed"

# 3. Remove Docker cluster container
echo "[3/10] Removing Docker containers..."
docker rm -f openshell-cluster-nemoclaw 2>/dev/null || true
docker rm -f openshell-cluster-openshell 2>/dev/null || true
docker ps -a --format "{{.Names}}" 2>/dev/null | grep -iE "openshell|nemoclaw|k3s" | xargs -I{} docker rm -f {} 2>/dev/null || true
echo "  OK Containers removed"

# 4. Remove Docker networks
echo "[4/10] Removing Docker networks..."
docker network rm openshell-cluster-nemoclaw 2>/dev/null || true
docker network rm openshell-network 2>/dev/null || true
docker network ls --format "{{.Name}}" 2>/dev/null | grep -iE "openshell|nemoclaw" | xargs -I{} docker network rm {} 2>/dev/null || true
echo "  OK Networks removed"

# 5. Remove Docker volumes
echo "[5/10] Removing Docker volumes..."
docker volume ls -q 2>/dev/null | grep -iE "openshell|nemoclaw|k3s" | xargs -I{} docker volume rm -f {} 2>/dev/null || true
echo "  OK Volumes removed"

# 6. Remove host config directories
echo "[6/10] Removing host config directories..."
rm -rf ~/.nemoclaw && echo "  OK ~/.nemoclaw removed"
rm -rf ~/.openclaw && echo "  OK ~/.openclaw removed"

# 7. Remove OpenShell/NemoClaw binaries
echo "[7/10] Removing binaries..."
rm -f ~/.local/bin/openshell && echo "  OK ~/.local/bin/openshell removed"
rm -f /usr/local/bin/openshell 2>/dev/null && echo "  OK /usr/local/bin/openshell removed"
rm -f /usr/local/bin/nemoclaw 2>/dev/null && echo "  OK /usr/local/bin/nemoclaw removed"

# 8. Remove NemoClaw source directory
echo "[8/10] Removing NemoClaw source..."
rm -rf /Users/mck/Desktop/NemoClaw && echo "  OK /Users/mck/Desktop/NemoClaw removed"

# 9. Remove MilimoClaw build artifacts
echo "[9/10] Removing build artifacts..."
rm -rf /Users/mck/Desktop/MilimoClaw/dist-bundle 2>/dev/null || true
rm -f /tmp/milimo-*.tar.gz /tmp/milimo-*.py /tmp/milimo-config.* /tmp/milimo-register.* 2>/dev/null || true
echo "  OK Build artifacts removed"

# 10. Final verification
echo "[10/10] Final verification..."
echo ""
remaining_containers=$(docker ps -a --format "{{.Names}}" 2>/dev/null | grep -ciE "openshell|nemoclaw|k3s" || echo "0")
remaining_networks=$(docker network ls 2>/dev/null | grep -ciE "openshell|nemoclaw" || echo "0")
remaining_volumes=$(docker volume ls 2>/dev/null | grep -ciE "openshell|nemoclaw|k3s" || echo "0")
remaining_processes=$(ps aux | grep -ciE "openshell|nemoclaw|k3s|ssh-proxy.*gateway" || echo "0")

echo "  Containers: $remaining_containers"
echo "  Networks:   $remaining_networks"
echo "  Volumes:    $remaining_volumes"
echo "  Processes:  $remaining_processes"
echo "  ~/.nemoclaw: $(test -d ~/.nemoclaw && echo 'EXISTS' || echo 'GONE')"
echo "  ~/.openclaw: $(test -d ~/.openclaw && echo 'EXISTS' || echo 'GONE')"
echo "  NemoClaw source: $(test -d /Users/mck/Desktop/NemoClaw && echo 'EXISTS' || echo 'GONE')"
echo ""

if [ "$remaining_containers" = "0" ] && [ "$remaining_networks" = "0" ] && [ "$remaining_volumes" = "0" ]; then
  echo "========================================================="
  echo "       OK  FULLY CLEAN - Ready for reinstall"
  echo "========================================================="
else
  echo "WARNING: Some artifacts remain - check the list above"
fi
