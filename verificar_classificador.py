"""Checagens do Laboratório K (Green Belt, Módulo 4, Aula 3). Rode com: python verificar_classificador.py

Confere o schema, a validação, as regras de revisão, o classificador contra os casos de teste e os commits.
Não altera nada no repositório.
"""
import os
import re
import subprocess
import importlib.util
import sys

sys.dont_write_bytecode = True  # não deixa __pycache__ para trás

OK, FALHA = "✅", "❌"
resultados = []


def checar(descricao, condicao, dica=""):
    resultados.append(bool(condicao))
    print(f"{OK if condicao else FALHA} {descricao}")
    if not condicao and dica:
        print(f"   → {dica}")


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip()


def ler(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
chave = os.environ.get("GEMINI_API_KEY", "")

print("\n1 · Arquivos")
fonte = ler("classificador.py")
checar("classificador.py existe", fonte is not None, "Copie o classificador.py do kit do Laboratório K para a raiz do repositório.")
checar("casos_teste.json existe", ler("casos_teste.json") is not None, "Copie o casos_teste.json do kit para a raiz do repositório.")
req = (ler("requirements.txt") or "").lower()
checar("requirements.txt lista pydantic", "pydantic" in req, "Acrescente uma linha com pydantic ao requirements.txt e rode pip install -r requirements.txt.")
if fonte is None:
    print("\nResultado: copie os arquivos do kit e rode de novo.")
    sys.exit(1)
checar("classificador.py não tem chave escrita no código",
       (not chave or chave not in fonte) and not re.search(r"(SUA_CHAVE|YOUR_API_KEY|AIza[0-9A-Za-z_\-]{20,})", fonte),
       "Leia a chave do ambiente (GEMINI_API_KEY), nunca escreva no código.")

print("\n2 · Contrato (schema e validação)")
try:
    spec = importlib.util.spec_from_file_location("classificador", "classificador.py")
    cl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cl)
    carregou = True
except Exception as e:
    carregou = False
    checar("classificador.py roda sem erro", False, f"{type(e).__name__}: {e}")

if carregou:
    props = cl.Classificacao.model_json_schema().get("properties", {})
    esperados = {"intencao", "urgencia", "resumo", "precisa_revisao_humana", "motivo_revisao"}
    checar("Classificacao tem os cinco campos do contrato", set(props) == esperados,
           f"Campos encontrados: {sorted(props)}. Cole a classe do notebook (TODO 1).")
    contrato_ok = set(props) == esperados
    if props:
        checar("Sem campo de confiança autodeclarada", not any("confi" in p for p in props),
               "A confiança declarada pelo modelo não é calibrada: use precisa_revisao_humana com regras.")
    if contrato_ok:
        checar("intencao aceita só as quatro categorias",
               sorted(props["intencao"].get("enum", [])) == ["comercial", "financeiro", "outros", "suporte"],
               "Use Literal[\"comercial\", \"suporte\", \"financeiro\", \"outros\"].")
        checar("urgencia aceita só baixa, media e alta", sorted(props["urgencia"].get("enum", [])) == ["alta", "baixa", "media"],
               "Use Literal[\"baixa\", \"media\", \"alta\"].")
    valido = '{"intencao": "comercial", "urgencia": "baixa", "resumo": "Pergunta sobre preço.", "precisa_revisao_humana": false, "motivo_revisao": ""}'
    invalidos = [valido.replace('"comercial"', '"vendas"'), valido.replace('false, "motivo_revisao": ""', 'true, "motivo_revisao": ""'),
                 "Claro! Aqui está: " + valido]
    c, _ = cl.validar(valido)
    checar("validar aceita uma classificação correta", c is not None, "Cole a função validar do notebook (TODO 2).")
    if c is not None:
        checar("validar recusa categoria fora da lista, revisão sem motivo e texto antes do JSON",
               all(cl.validar(t)[0] is None for t in invalidos), "Confira o Literal e o model_validator da revisão.")
    contrato_ok = contrato_ok and c is not None

    print("\n3 · Regras de revisão no código")
    if not contrato_ok:
        print("⚠️  Complete os TODOs 1 e 2 (schema e validação) para testar as regras.")
    else:
        fin = cl.aplicar_regras(c.model_copy(update={"intencao": "financeiro"}))
        alta = cl.aplicar_regras(c.model_copy(update={"urgencia": "alta"}))
        checar("Intenção financeira sempre vai para revisão, com motivo", fin.precisa_revisao_humana and fin.motivo_revisao.strip(),
               "Cole a função aplicar_regras do notebook (TODO 3).")
        checar("Urgência alta sempre vai para revisão, com motivo", alta.precisa_revisao_humana and alta.motivo_revisao.strip())
        checar("Mensagem comercial de urgência baixa não é alterada", cl.aplicar_regras(c) == c)

    print("\n4 · Classificador com o Gemini")
    if not contrato_ok:
        print("⚠️  Complete os TODOs 1 a 3 para testar o classificador.")
    elif len(chave) > 20:
        m04 = cl.classificar("Já mandei 3 emails e NINGUÉM responde!!! Cadê a minha turma de Power BI que era pra ter começado???")
        checar("classificar devolve uma Classificacao", isinstance(m04, cl.Classificacao))
        checar("A saída do modelo passa na validação (não caiu na falha segura)", m04 != cl.FALHA,
               "Confira a chave, o modelo e o FORMATO_SAIDA (troque para \"responseJsonSchema\" se a API recusar).")
        if m04 != cl.FALHA:
            print("   Rodando os casos de teste...")
            _, acertos = cl.rodar_casos()
            checar("Intenção certa em pelo menos 70% dos casos com gabarito", acertos["intencao"] >= 0.7,
                   "Revise as definições das categorias na instrução de sistema.")
            checar("Revisão humana certa em pelo menos 80% dos casos", acertos["revisao"] >= 0.8,
                   "Confira as regras de revisão, no prompt e em aplicar_regras.")
    else:
        print("⚠️  GEMINI_API_KEY não encontrada no ambiente: não deu para testar o classificador com o Gemini.")

print("\n5 · Commits")
rastreados = git("ls-files").splitlines()
checar("classificador.py e casos_teste.json estão no repositório", {"classificador.py", "casos_teste.json"} <= set(rastreados),
       "Rode: git add classificador.py casos_teste.json requirements.txt e faça commit.")
msgs = git("log", "--format=%s", "--", "classificador.py").splitlines()
vagas = [m for m in msgs if len(m.strip()) < 12 or m.strip().lower() in {"update", "teste", "ajuste", "wip", "fix", "."}]
if not msgs:
    checar("Há commit com o classificador", False, "Faça commit: git commit -m \"Adiciona classificador de mensagens com schema\"")
else:
    checar("Mensagens de commit claras no classificador", not vagas,
           f"Mensagens vagas: {vagas}. Diga o que mudou: 'Adiciona classificador de mensagens com schema'.")
status = git("status", "-sb").splitlines()
checar("Tudo enviado ao GitHub (push)", bool(status) and "ahead" not in status[0] and "origin/" in status[0], "Rode: git push")
pendentes = [l for l in status[1:] if l.strip()]
checar("Nenhuma mudança esquecida fora de commit", not pendentes, f"Arquivos pendentes: {pendentes}. Faça add e commit.")

print()
print("Resultado:", "tudo certo! ✅" if all(resultados) else f"{resultados.count(False)} item(ns) para corrigir.")
