#!/usr/bin/env bash
# Exporta todos os workflows do n8n para a pasta automacoes/, um arquivo por workflow,
# com o nome do workflow no nome do arquivo. Depois é só fazer commit.
# O export NÃO leva senhas nem chaves: credenciais aparecem só pelo nome e pelo id.
# Uso: bash n8n/exportar.sh
set -uo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$RAIZ/automacoes"

falha() { echo; echo "❌ $1"; [ -n "${2:-}" ] && echo "   → $2"; exit 1; }

# 1. O Docker e o contêiner do n8n
command -v docker >/dev/null 2>&1 || falha "o comando docker não existe neste ambiente." \
  "rode no terminal do Codespaces (não no seu computador) e crie o codespace com a configuração padrão."
docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx n8n || falha "o contêiner do n8n ainda não existe." \
  "rode primeiro: bash n8n/iniciar.sh"
if [ "$(docker inspect -f '{{.State.Running}}' n8n 2>/dev/null)" != "true" ]; then
  falha "o n8n está parado (o codespace foi desligado desde a última vez)." "rode: bash n8n/iniciar.sh  e depois este script de novo."
fi

# 2. O export dentro do contêiner (as mensagens do n8n vão para um log, para não poluir a tela)
LOG="$(mktemp)"
if ! docker exec -e N8N_DIAGNOSTICS_ENABLED=false n8n sh -c \
     'rm -rf /tmp/export && mkdir -p /tmp/export && n8n export:workflow --all --separate --pretty --output=/tmp/export/' >"$LOG" 2>&1; then
  if grep -q "No workflows found" "$LOG"; then
    rm -f "$LOG"
    falha "o n8n ainda não tem nenhum workflow salvo." \
      "no editor do n8n, salve o workflow (Ctrl+S, ou o botão Save) e rode este script de novo."
  fi
  echo; echo "❌ o n8n não conseguiu exportar. Últimas linhas da mensagem:"
  tail -n 15 "$LOG" | sed 's/^/   /'
  rm -f "$LOG"
  exit 1
fi
rm -f "$LOG"

# 3. Copia para fora do contêiner e grava em automacoes/, sem os campos que mudam a cada salvamento
TMP="$RAIZ/.export_tmp"
rm -rf "$TMP" && mkdir -p "$TMP"
docker cp n8n:/tmp/export/. "$TMP/" >/dev/null || { rm -rf "$TMP"; falha "não deu para copiar o export do contêiner." "rode de novo; se repetir, rode bash n8n/iniciar.sh"; }

python3 - "$RAIZ" <<'PY'
import json, pathlib, re, sys, unicodedata
raiz = pathlib.Path(sys.argv[1]); tmp = raiz / ".export_tmp"; destino = raiz / "automacoes"
VOLATEIS = ("createdAt", "updatedAt", "versionId", "activeVersionId", "versionCounter", "shared", "meta", "triggerCount", "versionMetadata")
usados = set(); total = 0
for arq in sorted(tmp.glob("*.json")):
    wf = json.loads(arq.read_text(encoding="utf-8"))
    if wf.get("isArchived"):
        continue
    for k in VOLATEIS:
        wf.pop(k, None)
    nome = unicodedata.normalize("NFKD", wf.get("name", "workflow")).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-") or "workflow"
    if slug in usados:
        slug += "-" + wf["id"][:6]
    usados.add(slug)
    (destino / f"{slug}.json").write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  automacoes/{slug}.json  ←  {wf.get('name')}")
    total += 1
if total == 0:
    print("  (nenhum workflow ativo para exportar: os que estavam no n8n estão arquivados)")
PY
STATUS=$?
rm -rf "$TMP"
[ $STATUS -eq 0 ] || falha "erro ao gravar os arquivos em automacoes/." "confira se a pasta automacoes/ existe e se você tem permissão de escrita nela."
echo "Pronto. Confira com 'git status' e faça o commit."
