# Módulo 5 · Arquivos para o repositório `assistente-de-cursos`

Copie tudo para a **raiz** do seu repositório (no Codespaces, arraste para o Explorer do VS Code) e faça um commit:

```
git add .gitattributes n8n automacoes testes verificar_n8n.py servico_classificador.py
git commit -m "Adiciona scripts do n8n (Módulo 5)"
git push
```

| Arquivo | Para que serve |
|---|---|
| `n8n/iniciar.sh` | Sobe o n8n (Community Edition) em Docker dentro do codespace. Rode `bash n8n/iniciar.sh`. |
| `n8n/exportar.sh` | Exporta os workflows do n8n para `automacoes/`, um arquivo por workflow, sem senhas nem chaves. |
| `automacoes/` | Onde ficam os workflows exportados, que vão para o Git. |
| `verificar_n8n.py` | Checagens dos laboratórios: `python verificar_n8n.py L` (Aula 1) e `python verificar_n8n.py M` (Aula 2) `python verificar_n8n.py N` (Aula 3, com o serviço rodando) e `python verificar_n8n.py O` / `O --sem-servico` (Aula 4). |
| `testes/leads_teste.json` | Aula 2: nove leads **fictícios** (L01 a L09) com o status esperado de cada um. |
| `servico_classificador.py` | Aula 3: o classificador do Lab K como serviço HTTP. Rode num terminal só para ele: `uvicorn servico_classificador:app --host 0.0.0.0 --port 8000`. Precisa de `fastapi` e `uvicorn` no `requirements.txt` e do `SERVICO_TOKEN` no `.env`. |
| `testes/testar_servico.py` | Aula 3: confere o serviço (saúde, recusa sem token, três classificações) sem mostrar segredos. |
| `testes/leads_classificar.json` | Aula 3: cinco leads fictícios (C01 a C05) com a rota esperada. |
| `testes/leads_estranhos.json` | Aula 4: leads com dados em formato inesperado (E01 e E02) e a mensagem longa da variação (E03). |
| `automacoes/diario-de-falhas.md` | Aula 4: modelo do diário do Laboratório O, para preencher antes e depois dos consertos. |
| `testes/enviar_leads.py` | Aula 2: envia os leads ao webhook. `python testes/enviar_leads.py` (URL de teste, só o L02), `--producao` (todos, workflow publicado), `--producao L09` (variação). Aula 3: `--classificar` (C01 a C05, confere a rota) e `--classificar --variacao`. Aula 4: `--classificar --sem-servico` e `--estranhos`. |

O n8n para quando o codespace desliga: rode `bash n8n/iniciar.sh` de novo ao voltar. Se o codespace for apagado,
o que não foi exportado para `automacoes/` e enviado ao GitHub se perde.

**Aula 2:** os leads de teste são fictícios (domínio `email.exemplo`). Não use dados de pessoas reais nos testes.
A Data Table com os leads fica no n8n e não vai para o Git: só o workflow é exportado.

**Aula 3:** gere o token do serviço e guarde no `.env` (que nunca vai para o Git):
`echo "SERVICO_TOKEN=$(python -c 'import secrets; print(secrets.token_urlsafe(24))')" >> .env`
A chave do Gemini continua nos Secrets do Codespaces e só o serviço a usa; o n8n recebe apenas o token, numa credencial.

**Aula 4:** antes de quebrar o fluxo de propósito, confira que o Laboratório N está commitado. O workflow **Alerta de falhas** precisa estar **publicado** para ser chamado.
