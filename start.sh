#!/bin/bash
# ============================================================
#  DTNum Labs — Script de démarrage complet
#  Usage : sudo ./start.sh [IP_SERVEUR]
#  Exemple : sudo ./start.sh 10.10.5.20
# ============================================================

set -e

DOMAIN="dtnum.nubo.local"
IP=${1:-"127.0.0.1"}

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        DTNum Labs — Démarrage complet        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. VÉRIFICATIONS ─────────────────────────────────────────
echo -e "${YELLOW}[1/7] Vérifications...${NC}"
command -v docker &>/dev/null || { echo -e "${RED}  ✗ Docker non installé${NC}"; exit 1; }
echo -e "${GREEN}  ✓ Docker${NC}"
command -v docker-compose &>/dev/null || { echo -e "${RED}  ✗ docker-compose non installé${NC}"; exit 1; }
echo -e "${GREEN}  ✓ docker-compose${NC}"
command -v curl &>/dev/null || sudo apt install curl -y -q
echo -e "${GREEN}  ✓ curl${NC}"

# ── 2. DNS ───────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/7] Configuration DNS...${NC}"
sudo sed -i "/$DOMAIN/d" /etc/hosts
echo "$IP  $DOMAIN" | sudo tee -a /etc/hosts > /dev/null
echo -e "${GREEN}  ✓ $IP → $DOMAIN${NC}"

# ── 3. NETTOYAGE CONFIGS NGINX ORPHELINES ────────────────────
echo ""
echo -e "${YELLOW}[3/7] Nettoyage des configs Nginx orphelines...${NC}"
CLEANED=0
for conf in nginx/services/*.conf; do
    [ -f "$conf" ] || continue
    name=$(basename "$conf" .conf)
    if ! sudo docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        sudo rm -f "$conf"
        echo -e "${YELLOW}  ~ Supprimé : $name${NC}"
        CLEANED=$((CLEANED+1))
    fi
done
[ $CLEANED -eq 0 ] && echo -e "${GREEN}  ✓ Aucun orphelin${NC}" || echo -e "${GREEN}  ✓ $CLEANED fichier(s) supprimé(s)${NC}"

# ── 4. DÉMARRAGE ─────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/7] Démarrage de la stack...${NC}"
sudo docker-compose down 2>/dev/null || true
sudo docker rm -f dtnum-cert-generator 2>/dev/null || true
sudo docker-compose up -d
echo -e "${GREEN}  ✓ Stack démarrée${NC}"

# ── 5. CERTIFICAT ────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/7] Certificat TLS...${NC}"
for i in $(seq 1 30); do
    STATUS=$(sudo docker inspect dtnum-cert-generator --format='{{.State.Status}}' 2>/dev/null || echo "")
    [ "$STATUS" = "exited" ] && break
    sleep 2
done
EXIT_CODE=$(sudo docker inspect dtnum-cert-generator --format='{{.State.ExitCode}}' 2>/dev/null || echo "1")
[ "$EXIT_CODE" = "0" ] && echo -e "${GREEN}  ✓ Certificat généré${NC}" || { echo -e "${RED}  ✗ Erreur certificat${NC}"; exit 1; }
sudo docker-compose restart nginx >/dev/null 2>&1
echo -e "${GREEN}  ✓ Nginx rechargé${NC}"

# ── 6. ATTENTE KEYCLOAK ──────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/7] Attente de Keycloak...${NC}"
WAITED=0
until sudo docker exec dtnum-keycloak /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080/auth --realm master \
    --user admin --password Keycloak@2026! >/dev/null 2>&1; do
    echo -ne "  Attente... ${WAITED}s\r"
    sleep 5; WAITED=$((WAITED+5))
    [ $WAITED -gt 180 ] && { echo -e "${RED}  ✗ Timeout Keycloak${NC}"; exit 1; }
done
echo -e "${GREEN}  ✓ Keycloak prêt (${WAITED}s)          ${NC}"

# ── 7. INITIALISATION KEYCLOAK ───────────────────────────────
echo ""
echo -e "${YELLOW}[7/7] Initialisation Keycloak...${NC}"

sudo docker exec dtnum-keycloak /opt/keycloak/bin/kcadm.sh create realms \
    -s realm=datalab -s enabled=true 2>/dev/null \
    && echo -e "${GREEN}  ✓ Realm 'datalab' créé${NC}" \
    || echo -e "${YELLOW}  ~ Realm existe déjà${NC}"

sudo docker exec dtnum-keycloak /opt/keycloak/bin/kcadm.sh create clients \
    -r datalab -s clientId=datalab-lite -s enabled=true \
    -s publicClient=true -s directAccessGrantsEnabled=true \
    -s "redirectUris=[\"https://$DOMAIN/*\"]" \
    -s "webOrigins=[\"https://$DOMAIN\"]" 2>/dev/null \
    && echo -e "${GREEN}  ✓ Client 'datalab-lite' créé${NC}" \
    || echo -e "${YELLOW}  ~ Client existe déjà${NC}"

create_user() {
    local U=$1 P=$2
    sudo docker exec dtnum-keycloak /opt/keycloak/bin/kcadm.sh config credentials \
        --server http://localhost:8080/auth --realm master \
        --user admin --password Keycloak@2026! >/dev/null 2>&1
    sudo docker exec dtnum-keycloak /opt/keycloak/bin/kcadm.sh create users \
        -r datalab -s username="$U" -s enabled=true -s emailVerified=true 2>/dev/null || true
    sudo docker exec dtnum-keycloak /opt/keycloak/bin/kcadm.sh set-password \
        -r datalab --username "$U" --new-password "$P" 2>/dev/null
    echo -e "${GREEN}  ✓ $U${NC}"
}

create_user "admin-dtnum" "Admin@2026!"
create_user "user1"       "User1@2026!"
create_user "user2"       "User2@2026!"

# ── RÉSUMÉ ───────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           DTNum Labs est prêt ! ✅           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Portail   : ${GREEN}https://$DOMAIN${NC}"
echo -e "  Status    : ${GREEN}https://$DOMAIN/status${NC}"
echo -e "  Keycloak  : ${GREEN}https://$DOMAIN/auth${NC}   (admin / Keycloak@2026!)"
echo -e "  MinIO     : ${GREEN}https://$DOMAIN/minio${NC}  (admin / Minio@2026!)"
echo ""
echo -e "  Utilisateurs :"
echo -e "  ┌─────────────┬─────────────┐"
echo -e "  │ admin-dtnum │ Admin@2026! │"
echo -e "  │ user1       │ User1@2026! │"
echo -e "  │ user2       │ User2@2026! │"
echo -e "  └─────────────┴─────────────┘"
echo ""
echo -e "  Acces services :"
echo -e "  • JupyterLab  → ${GREEN}https://$DOMAIN/{nom}/lab?token={token}${NC}"
echo -e "  • RStudio     → ${YELLOW}http://$DOMAIN:PORT/${NC}  (login: rstudio / token)"
echo -e "  • VSCode      → ${YELLOW}http://$DOMAIN:PORT/${NC}  (login: token)"
echo ""
echo -e "${YELLOW}  ⚠ Certificat auto-signé : accepter l'avertissement navigateur${NC}"
echo ""
