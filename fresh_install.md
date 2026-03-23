# === PHASE 1: CLEAN SLATE ===
docker stop MilimoClaw openshell-cluster-nemoclaw
docker rm MilimoClaw openshell-cluster-nemoclaw
docker rmi milimo-claw:latest milimoclaw-sandbox:latest nemoclaw-tool:latest
docker image prune -f
rm -rf ~/.nemoclaw ~/.openclaw ~/.milimo ~/.config/openshell
npm uninstall -g nemoclaw openclaw

# === PHASE 2: FRESH NEMOCLAW ===
cd ~
git clone https://github.com/NVIDIA/NemoClaw.git
cd NemoClaw
./install.sh
nemoclaw onboard  # Follow prompts

# === PHASE 3: MILIMO CLAW ===
cd /Users/mck/Desktop/MilimoClaw
npm run build -w milimo
cd milimo && tar czf ../milimo-plugin.tar.gz dist/ openclaw.plugin.json package.json
openshell sandbox upload <sandbox-name> --upload /Users/mck/Desktop/MilimoClaw/milimo-plugin.tar.gz:/tmp/

# Connect and install
openshell sandbox connect <sandbox-name>
# Inside: cd /tmp && tar xzf milimo-plugin.tar.gz && openclaw plugins install .

# === PHASE 4: MILIMO ONBOARDING ===
# Inside sandbox: openclaw milimo onboard
