#!/usr/bin/env bash
# Sobe o n8n (Community Edition) em Docker, dentro do Codespaces.
# Uso: bash n8n/iniciar.sh
# Os dados do n8n (conta, workflows, execuções) ficam no volume Docker "n8n_data",
# que dura enquanto o codespace existir. Para guardar os workflows no Git, use n8n/exportar.sh.
set -euo pipefail

VERSAO="${N8N_VERSAO:-2.41.3}"          # versão usada nas apostilas; o instrutor pode trocar
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$RAIZ/automacoes"

if [ -n "${CODESPACE_NAME:-}" ]; then
  URL="https://${CODESPACE_NAME}-5678.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}/"
else
  URL="http://localhost:5678/"
fi

if docker ps -a --format '{{.Names}}' | grep -qx n8n; then
  echo "Contêiner n8n já existe: iniciando."
  docker start n8n >/dev/null
else
  echo "Criando o contêiner n8n (versão $VERSAO). Na primeira vez, o download leva alguns minutos."
  docker run -d --name n8n --restart unless-stopped \
    -p 5678:5678 \
    -e GENERIC_TIMEZONE="America/Sao_Paulo" -e TZ="America/Sao_Paulo" \
    -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
    -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false \
    -e WEBHOOK_URL="$URL" -e N8N_EDITOR_BASE_URL="$URL" \
    -e N8N_PROXY_HOPS=1 -e N8N_PUSH_BACKEND=sse \
    -v n8n_data:/home/node/.n8n \
    -v "$RAIZ/automacoes:/home/node/automacoes" \
    --add-host=host.docker.internal:host-gateway \
    "n8nio/n8n:$VERSAO" >/dev/null
fi

printf "Esperando o n8n responder"
for _ in $(seq 1 90); do
  if curl -fs http://localhost:5678/healthz >/dev/null 2>&1; then
    echo; echo "n8n no ar. Abra no navegador: $URL"
    echo "(ou pela aba PORTS do VS Code, porta 5678)"
    exit 0
  fi
  printf "."; sleep 2
done
echo; echo "O n8n não respondeu em 3 minutos. Veja o log com: docker logs n8n --tail 50"
exit 1
