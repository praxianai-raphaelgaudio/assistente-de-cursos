"""Envia leads de teste (fictícios) para o webhook do n8n.

Uso:
  python testes/enviar_leads.py L02            envia o L02 para a URL de TESTE (clique antes em "Listen for test event")
  python testes/enviar_leads.py --producao     envia todos para a URL de PRODUÇÃO (o workflow precisa estar publicado)
  python testes/enviar_leads.py --producao L03 envia só o L03 para produção
  python testes/enviar_leads.py --producao L09 testa a variação 6.5 (o L09 só vai quando você pede)

O n8n roda no seu codespace; por isso o endereço é localhost:5678. Os dados são fictícios.
"""
import json, pathlib, sys
import requests

PASTA = pathlib.Path(__file__).resolve().parent
SEM_SERVICO = False
BASE = "http://localhost:5678"
CAMINHO = "leads"


def carregar(arquivo="leads_teste.json"):
    return json.loads((PASTA / arquivo).read_text(encoding="utf-8"))


def enviar(lead, producao, variacao=False):
    global SEM_SERVICO
    url = f"{BASE}/{'webhook' if producao else 'webhook-test'}/{CAMINHO}"
    try:
        r = requests.post(url, json=lead["corpo"], timeout=90)
    except requests.RequestException as e:
        print(f"{lead['id']}  sem resposta ({type(e).__name__}): o n8n está no ar? rode bash n8n/iniciar.sh")
        return None
    try:
        corpo = r.json()
    except ValueError:
        corpo = r.text[:200]
    if isinstance(corpo, dict) and "stacktrace" in corpo:
        corpo = {"message": corpo.get("message")}  # erro do próprio n8n: só a mensagem interessa
    marca = "✅" if r.status_code == lead["esperado"] else "❌"
    rota_esperada = lead.get("rota_variacao", lead.get("rota")) if variacao else lead.get("rota")
    if SEM_SERVICO and "rota" in lead:
        rota_esperada = "revisao"
    if "rota" in lead:  # Aula 3: além do código, confere a rota
        rota = corpo.get("rota") if isinstance(corpo, dict) else None
        certo = r.status_code == lead["esperado"] and rota == rota_esperada
        marca = "✅" if certo else "❌"
        detalhe = f"rota {rota}" + ("" if rota == rota_esperada else f" (esperada {rota_esperada})")
        print(f"{marca} {lead['id']}  {r.status_code}  {detalhe}  ·  {corpo.get('confirmacao', '') if isinstance(corpo, dict) else corpo}")
        if r.status_code == 404:
            print("   → o workflow está publicado (Publish)? O caminho do webhook é 'leads'?")
        if r.status_code >= 500:
            print("   → a execução falhou no meio: abra a aba Executions (e a tabela falhas, se o alerta estiver ligado)")
        return certo
    esperado = "" if r.status_code == lead["esperado"] else f" (esperado {lead['esperado']})"
    print(f"{marca} {lead['id']}  {r.status_code}{esperado}  {json.dumps(corpo, ensure_ascii=False)}")
    if r.status_code == 404 and not producao:
        print("   → a URL de teste só aceita uma chamada por clique em “Listen for test event”.")
    if r.status_code == 404 and producao:
        print("   → o workflow está publicado (Publish)? O caminho do webhook é 'leads'?")
    if r.status_code >= 500:
        print("   → a execução falhou no meio: abra a aba Executions (e a tabela falhas, se o alerta estiver ligado)")
    return r.status_code == lead["esperado"]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    producao = any(a in sys.argv for a in ("--producao", "--classificar", "--estranhos"))
    variacao = "--variacao" in sys.argv
    SEM_SERVICO = "--sem-servico" in sys.argv
    if SEM_SERVICO:
        try:
            requests.get("http://localhost:8000/saude", timeout=3, proxies={"http": None, "https": None})
            sys.exit("O serviço do classificador ainda está no ar. Pare-o (Ctrl+C no terminal dele) e rode de novo.")
        except requests.RequestException:
            print("Serviço parado, como pedido: todos os leads devem ir para a revisão humana.\n")
    arquivo = "leads_teste.json"
    if "--classificar" in sys.argv:
        arquivo = "leads_classificar.json"
    elif "--estranhos" in sys.argv:
        arquivo = "leads_estranhos.json"
    leads = carregar(arquivo)
    if args:
        leads = [l for l in leads if l["id"] in {a.upper() for a in args}]
    else:
        leads = [l for l in leads if not l.get("variacao")]
    if not args and not producao:
        leads = [l for l in leads if l["id"] == "L02"]  # na URL de teste, só um por vez: o L02
    certos = [enviar(l, producao, variacao) for l in leads]
    print(f"\n{sum(1 for c in certos if c)} de {len(leads)} com o status esperado.")
