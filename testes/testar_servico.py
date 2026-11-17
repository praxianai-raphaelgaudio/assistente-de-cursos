"""Testa o serviço do classificador (Módulo 5, Aula 3) sem mostrar nenhum segredo.

Uso (com o serviço rodando em outro terminal):
    python testes/testar_servico.py
    python testes/testar_servico.py "Qual o horário de atendimento?"     classifica uma mensagem sua

Lê o SERVICO_TOKEN do ambiente ou do .env, como o próprio serviço.
"""
import json, os, sys
import requests
from dotenv import load_dotenv

load_dotenv()
BASE = "http://localhost:8000"
TOKEN = os.environ.get("SERVICO_TOKEN", "")
MENSAGENS = [
    "Tem turma de Python aos sábados? Quanto fica à vista?",
    "Não consigo acessar a plataforma das aulas desde ontem, dá erro de senha.",
    "Paguei a matrícula duas vezes no cartão!!! Quero o estorno urgente.",
]
sem_proxy = {"http": None, "https": None}


def main():
    try:
        saude = requests.get(f"{BASE}/saude", timeout=5, proxies=sem_proxy).json()
    except requests.RequestException:
        sys.exit("O serviço não respondeu em localhost:8000. Num terminal só para ele, rode:\n"
                 "  uvicorn servico_classificador:app --host 0.0.0.0 --port 8000")
    print("Saúde:", json.dumps(saude, ensure_ascii=False))
    if not TOKEN:
        sys.exit("SERVICO_TOKEN não encontrado no ambiente nem no .env.")
    r = requests.post(f"{BASE}/classificar", json={"mensagem": "teste"}, timeout=10, proxies=sem_proxy)
    print(f"Sem token: {r.status_code} {r.json().get('detail', '')}")
    for msg in sys.argv[1:] and [" ".join(sys.argv[1:])] or MENSAGENS:
        r = requests.post(f"{BASE}/classificar", json={"mensagem": msg}, headers={"X-Token": TOKEN},
                          timeout=90, proxies=sem_proxy)
        c = r.json()
        revisar = "  → revisão humana" if c.get("precisa_revisao_humana") else ""
        print(f"\n{r.status_code}  {msg}\n     {c.get('intencao')} · {c.get('urgencia')} · {c.get('resumo')}{revisar}")


if __name__ == "__main__":
    main()
