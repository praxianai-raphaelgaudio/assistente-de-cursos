"""Serviço do classificador (Green Belt, Módulo 5, Aula 3).

Expõe o classificador do Laboratório K (classificador.py) por HTTP, para o n8n chamar.
O contrato é o mesmo do Módulo 4: entra uma mensagem, sai uma Classificacao validada pelo Pydantic.

Rodar (num terminal só para ele):
    uvicorn servico_classificador:app --host 0.0.0.0 --port 8000

Configuração lida do ambiente (Secrets do Codespaces ou arquivo .env), nunca do código:
    GEMINI_API_KEY   chave do Gemini, usada só por este serviço
    SERVICO_TOKEN    senha que o n8n manda no cabeçalho X-Token (gere com: python -c "import secrets; print(secrets.token_urlsafe(24))")
"""
import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from classificador import CHAVE, MODELO, Classificacao, classificar

TOKEN = os.environ.get("SERVICO_TOKEN", "")

SEM_MENSAGEM = Classificacao(intencao="outros", urgencia="baixa", resumo="Lead sem mensagem.",
                             precisa_revisao_humana=True, motivo_revisao="Mensagem vazia: não há o que classificar.")

app = FastAPI(title="Classificador da Escola New Tech", version="1.0",
              description="Classifica mensagens de leads e alunos. Contrato do Módulo 4, Laboratório K.")


class Pedido(BaseModel):
    mensagem: str = Field(default="", max_length=2000, description="Só o texto da mensagem, sem nome, e-mail ou telefone.")


@app.get("/saude", summary="O serviço está no ar?")
def saude():
    """Diz se o serviço está no ar e se a configuração existe (sem mostrar nenhum valor)."""
    return {"status": "ok", "modelo": MODELO, "chave_configurada": bool(CHAVE), "token_configurado": bool(TOKEN)}


@app.post("/classificar", response_model=Classificacao, summary="Classificar uma mensagem")
def post_classificar(pedido: Pedido, x_token: str = Header(default="")):
    """Classifica uma mensagem. Exige o cabeçalho X-Token igual ao SERVICO_TOKEN."""
    if not TOKEN or not secrets.compare_digest(x_token, TOKEN):
        raise HTTPException(status_code=401, detail="token ausente ou inválido")
    if not pedido.mensagem.strip():
        return SEM_MENSAGEM  # nada para classificar: não gasta uma chamada ao modelo
    return classificar(pedido.mensagem)
