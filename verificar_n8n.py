"""Checagens dos laboratórios do Módulo 5 (n8n).

Uso:  python verificar_n8n.py L     (Laboratório L, Aula 1)
      python verificar_n8n.py M     (Laboratório M, Aula 2)
      python verificar_n8n.py N     (Laboratório N, Aula 3: o serviço do classificador precisa estar rodando)
      python verificar_n8n.py O     (Laboratório O, Aula 4: com o serviço rodando)
      python verificar_n8n.py O --sem-servico   (Laboratório O: com o serviço parado, confere o caminho de falha)

Confere o n8n no ar, o workflow exportado em automacoes/, a ausência de segredos e o commit.
As dicas dizem o que olhar; nada aqui altera os seus arquivos.
"""
import json, os, pathlib, re, subprocess, sys, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent
PASTA = RAIZ / "automacoes"
falhas = 0


def checar(nome, ok, dica=""):
    global falhas
    print(("✅ " if ok else "❌ ") + nome)
    if not ok:
        falhas += 1
        if dica:
            print("   → " + dica)
    return ok


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True)
    return r.stdout.strip()


def workflows():
    for arq in sorted(PASTA.glob("*.json")):
        try:
            yield arq, json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            yield arq, None


def achar(nome_procurado):
    alvo = nome_procurado.lower()
    for arq, wf in workflows():
        if wf and wf.get("name", "").strip().lower() == alvo:
            return arq, wf
    return None, None


def tipos(wf):
    return [n.get("type", "").split(".")[-1] for n in wf.get("nodes", [])]


def n8n_no_ar():
    try:
        abrir = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
        with abrir("http://localhost:5678/healthz", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def segredos():
    padroes = [r"AIza[0-9A-Za-z_\-]{20,}", r"sk-[0-9A-Za-z]{20,}", r"x-goog-api-key\"\s*:\s*\"[^\"{]"]
    achados = []
    for arq in PASTA.glob("*.json"):
        texto = arq.read_text(encoding="utf-8", errors="ignore")
        if any(re.search(p, texto) for p in padroes):
            achados.append(arq.name)
    return achados


def comum():
    print("\n== Ambiente e segurança ==")
    checar("n8n respondendo em localhost:5678", n8n_no_ar(),
           "rode: bash n8n/iniciar.sh (o n8n para quando o codespace é desligado)")
    checar("pasta automacoes/ existe", PASTA.is_dir(), "rode: bash n8n/exportar.sh")
    invalidos = [a.name for a, wf in workflows() if wf is None]
    checar("todos os arquivos de automacoes/ são JSON válidos", not invalidos, f"arquivos com problema: {invalidos}")
    achados = segredos()
    checar("nenhuma chave de API nos workflows exportados", not achados,
           f"parece haver uma chave em {achados}: apague-a do n8n, troque a chave (vazou, trocou) e exporte de novo")


def lab_l():
    print("\n== Laboratório L: resumo das próximas turmas ==")
    nomes = [wf.get("name", "").strip().lower() for _, wf in workflows() if wf]
    checar("nenhum workflow repetido em automacoes/", len(nomes) == len(set(nomes)),
           "há dois workflows com o mesmo nome: apague a cópia no n8n e exporte de novo")
    arq, wf = achar("Resumo das próximas turmas")
    if not checar("workflow “Resumo das próximas turmas” exportado em automacoes/", wf is not None,
                  "confira o nome do workflow no n8n e rode: bash n8n/exportar.sh"):
        return
    t = tipos(wf)
    checar("começa com Manual Trigger", "manualTrigger" in t, "o primeiro nó deve ser o gatilho manual")
    http = [n for n in wf["nodes"] if n["type"].endswith("httpRequest")]
    checar("tem um HTTP Request que busca /catalogo.json",
           any(str(n.get("parameters", {}).get("url", "")).rstrip("/").endswith("/catalogo.json") for n in http),
           "o endereço deve terminar em /catalogo.json (endereço da API publicado no Classroom)")
    filtros = [n for n in wf["nodes"] if n["type"].endswith(".filter")]
    n_cond = sum(len(n.get("parameters", {}).get("conditions", {}).get("conditions", [])) for n in filtros)
    checar("filtra por mês e por modalidade (2 condições ou mais)", n_cond >= 2,
           "o nó Filter precisa de duas condições: mês da turma e modalidade")
    checar("ordena as turmas (Sort)", "sort" in t, "acrescente um nó Sort pelo campo proxima_turma")
    checar("monta campos com Edit Fields (Set)", t.count("set") >= 2,
           "use Edit Fields para a configuração, para a linha de cada curso e para o resumo")
    checar("junta as linhas num item só (Aggregate)", "aggregate" in t, "acrescente um nó Aggregate pelo campo linha")
    ligados = set(wf.get("connections", {}).keys()) | {c["node"] for v in wf.get("connections", {}).values()
                                                       for saida in v.get("main", []) for c in (saida or [])}
    soltos = [n["name"] for n in wf["nodes"] if n["name"] not in ligados and len(wf["nodes"]) > 1]
    checar("nenhum nó solto (todos conectados)", not soltos, f"nós sem conexão: {soltos}")
    rel = arq.relative_to(RAIZ).as_posix()
    checar(f"{rel} está no Git (commit feito)", rel in git("ls-files", "automacoes"),
           f"git add {rel} && git commit -m \"Adiciona workflow do resumo das próximas turmas\"")
    checar("commit enviado ao GitHub (push)", git("status", "-sb").find("ahead") == -1, "rode: git push")


def soltos_de(wf):
    ligados = set(wf.get("connections", {}).keys()) | {c["node"] for v in wf.get("connections", {}).values()
                                                       for saida in v.get("main", []) for c in (saida or [])}
    return [n["name"] for n in wf["nodes"] if n["name"] not in ligados and len(wf["nodes"]) > 1]


def postar(url, corpo):
    """POST JSON sem proxy; devolve (status, corpo em dict ou texto)."""
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    abrir = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    try:
        with abrir(req, timeout=90) as r:
            status, texto = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        status, texto = e.code, e.read().decode()
    except Exception as e:
        return None, str(e)
    try:
        return status, json.loads(texto)
    except json.JSONDecodeError:
        return status, texto


def lab_m():
    print("\n== Laboratório M: porta de entrada de leads ==")
    arq, wf = achar("Porta de entrada de leads")
    if not checar("workflow “Porta de entrada de leads” exportado em automacoes/", wf is not None,
                  "confira o nome do workflow no n8n e rode: bash n8n/exportar.sh"):
        return
    nos = wf.get("nodes", [])
    por_tipo = lambda t: [n for n in nos if n.get("type", "").endswith("." + t)]
    hooks = por_tipo("webhook")
    hp = hooks[0].get("parameters", {}) if hooks else {}
    checar("começa com um Webhook", bool(hooks), "o gatilho do Lab M é o nó Webhook")
    checar("Webhook com método POST e path leads", hp.get("httpMethod") == "POST" and hp.get("path") == "leads",
           "no Webhook: HTTP Method = POST e Path = leads")
    checar("Webhook responde pelo nó Respond to Webhook", hp.get("responseMode") == "responseNode",
           "no Webhook: Respond = Using 'Respond to Webhook' Node")
    checar("normaliza e confere com Edit Fields (2 nós ou mais)", len(por_tipo("set")) >= 2,
           "um Edit Fields para normalizar (Normalizar) e outro para listar os erros (Conferir)")
    checar("decide com um If", bool(por_tipo("if")), "acrescente o If “Dados válidos?” depois do Conferir")
    dts = por_tipo("dataTable")
    checar("registra o lead numa Data Table (insert)",
           any(n.get("parameters", {}).get("operation", "insert") == "insert" for n in dts),
           "no ramo true do If, use Data Table › Insert row na tabela leads")
    codigos = {str(n.get("parameters", {}).get("options", {}).get("responseCode", 200)) for n in por_tipo("respondToWebhook")}
    checar("responde 201 quando registra e 400 quando recusa", {"201", "400"} <= codigos,
           f"códigos encontrados nos Respond to Webhook: {sorted(codigos) or 'nenhum'}; use Options › Response Code")
    soltos = soltos_de(wf)
    checar("nenhum nó solto (todos conectados)", not soltos, f"nós sem conexão: {soltos}")
    checar("workflow publicado (Published)", wf.get("active") is True,
           "clique em Publish no alto do editor e exporte de novo")

    print("\n== Laboratório M: teste ao vivo (URL de produção) ==")
    url = "http://localhost:5678/webhook/leads"
    status, corpo = postar(url, {"nome": "  teste  VERIFICADOR ", "email": " Teste.Verificador@Email.EXEMPLO ",
                                 "telefone": "(11) 90000-0000", "curso": "nt-101 ", "mensagem": "teste automático",
                                 "origem": "verificador", "consentimento": True})
    if status is None or status == 404:
        checar("URL de produção responde", False,
               "o workflow precisa estar publicado; confira também o path leads e se o n8n está no ar")
        return
    checar("lead válido e bagunçado → 201", status == 201, f"resposta {status}: {str(corpo)[:120]}")
    email = corpo.get("email") if isinstance(corpo, dict) else None
    checar("e-mail normalizado na resposta (minúsculas, sem espaços)", email == "teste.verificador@email.exemplo",
           f"a resposta trouxe {email!r}; confira o trim() e o toLowerCase() no Normalizar e o corpo do Responder 201")
    status, corpo = postar(url, {"nome": "Teste Verificador", "email": "teste.verificador@", "origem": "verificador",
                                 "consentimento": True})
    checar("lead com e-mail inválido → 400", status == 400, f"resposta {status}: {str(corpo)[:120]}")
    erros = corpo.get("erros") if isinstance(corpo, dict) else None
    checar("resposta 400 lista os erros", isinstance(erros, list) and len(erros) >= 1,
           "o Responder 400 deve devolver { status: 'recusado', erros: $json.erros }")
    status, corpo = postar(url, {"nome": "Teste Verificador", "email": "teste.verificador@email.exemplo", "curso": "Python",
                                 "origem": "verificador", "consentimento": True})
    erros = corpo.get("erros") if isinstance(corpo, dict) else None
    checar("variação 6.5: curso fora do padrão NT-xxx → 400", status == 400 and any("curso" in str(e) for e in (erros or [])),
           "acrescente ao Conferir o erro 'código de curso inválido' quando curso não estiver vazio e não seguir NT-000")
    print("   (os leads de teste aceitos ficam na tabela com origem = verificador; pode apagar as linhas depois)")

    rel = arq.relative_to(RAIZ).as_posix()
    checar(f"{rel} está no Git (commit feito)", rel in git("ls-files", "automacoes"),
           f"git add {rel} && git commit -m \"Adiciona a porta de entrada de leads\"")
    checar("commit enviado ao GitHub (push)", git("status", "-sb").find("ahead") == -1, "rode: git push")


def ler_env(nome):
    """Valor de uma variável do ambiente ou do arquivo .env (só para comparar; nunca é impresso)."""
    if os.environ.get(nome):
        return os.environ[nome]
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.strip().startswith(nome + "="):
                return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def pegar(url, cabecalhos=None):
    req = urllib.request.Request(url, headers=cabecalhos or {})
    abrir = urllib.request.build_opener(urllib.request.ProxyHandler({})).open
    try:
        with abrir(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


LEADS_N = {
    "comercial": {"nome": "Teste Verificador", "email": "teste.comercial@email.exemplo", "curso": "NT-102", "origem": "verificador",
                  "consentimento": True, "mensagem": "Tem turma de Python aos sábados? Quanto fica à vista?"},
    "suporte": {"nome": "Teste Verificador", "email": "teste.suporte@email.exemplo", "curso": "NT-201", "origem": "verificador",
                "consentimento": True, "mensagem": "Não consigo acessar a plataforma das aulas desde ontem, dá erro de senha."},
    "outros": {"nome": "Teste Verificador", "email": "teste.outros@email.exemplo", "origem": "verificador",
               "consentimento": True, "mensagem": "Vocês alugam as salas de aula para eventos?"},
    "financeiro": {"nome": "Teste Verificador", "email": "teste.financeiro@email.exemplo", "curso": "NT-303", "origem": "verificador",
                   "consentimento": True, "mensagem": "Paguei a matrícula duas vezes no cartão!!! Quero o estorno urgente."},
}


def lab_n():
    print("\n== Laboratório N: o classificador no fluxo ==")
    arq, wf = achar("Porta de entrada de leads")
    if not checar("workflow “Porta de entrada de leads” exportado em automacoes/", wf is not None,
                  "confira o nome do workflow no n8n e rode: bash n8n/exportar.sh"):
        return
    nos = wf.get("nodes", [])
    por_tipo = lambda t: [n for n in nos if n.get("type", "").endswith("." + t)]
    cls = [n for n in por_tipo("httpRequest") if str(n.get("parameters", {}).get("url", "")).rstrip("/").endswith("/classificar")]
    checar("um HTTP Request chama o serviço em /classificar", bool(cls),
           "URL: http://host.docker.internal:8000/classificar (o n8n roda num contêiner; localhost seria o próprio contêiner)")
    if cls:
        cp = cls[0].get("parameters", {})
        checar("o HTTP Request usa POST", cp.get("method") == "POST", "Method: POST")
        checar("o token vem de uma credencial Header Auth, e não de um cabeçalho digitado no nó",
               cp.get("genericAuthType") == "httpHeaderAuth" and "httpHeaderAuth" in cls[0].get("credentials", {})
               and not cp.get("sendHeaders"),
               "Authentication: Generic Credential Type › Header Auth, com a credencial “Serviço classificador”; tire o X-Token de Send Headers")
        checar("o HTTP Request tem timeout", bool(cp.get("options", {}).get("timeout")), "Options › Add option › Timeout")
    sw = por_tipo("switch")
    regras = sw[0].get("parameters", {}).get("rules", {}).get("values", []) if sw else []
    checar("um Switch separa as rotas (3 regras ou mais)", len(regras) >= 3, "Switch “Rota” com as regras revisão, comercial e suporte")
    checar("o Switch tem a saída extra para o resto (fallback)",
           bool(sw) and sw[0].get("parameters", {}).get("options", {}).get("fallbackOutput") == "extra",
           "Switch › Options › Fallback Output: Extra Output (renomeie para outros)")
    if sw:
        saidas = wf.get("connections", {}).get(sw[0]["name"], {}).get("main", [])
        checar("todas as saídas do Switch estão ligadas", len(saidas) >= len(regras) + 1 and all(saidas),
               "uma saída sem ligação faz o lead sumir sem resposta")
    corpo201 = " ".join(str(n.get("parameters", {}).get("responseBody", "")) for n in por_tipo("respondToWebhook"))
    checar("a confirmação devolve a rota", "rota" in corpo201, "no Responder 201, inclua rota e confirmacao no corpo")
    soltos = soltos_de(wf)
    checar("nenhum nó solto (todos conectados)", not soltos, f"nós sem conexão: {soltos}")
    checar("workflow publicado (Published)", wf.get("active") is True, "clique em Publish e exporte de novo")

    print("\n== Laboratório N: segredos ==")
    token = ler_env("SERVICO_TOKEN")
    checar("SERVICO_TOKEN configurado (Secrets do Codespaces ou .env)", bool(token),
           "gere um token e ponha no .env: SERVICO_TOKEN=... (veja a seção 3 da apostila)")
    textos = [a.read_text(encoding="utf-8", errors="ignore") for a in PASTA.glob("*.json")]
    for nome in ("SERVICO_TOKEN", "GEMINI_API_KEY"):
        valor = ler_env(nome)
        checar(f"o valor de {nome} não aparece em automacoes/", not valor or all(valor not in t for t in textos),
               f"o valor de {nome} foi parar num workflow: tire-o do nó, troque o segredo (vazou, trocou) e exporte de novo")
    checar(".env fora do Git", not git("ls-files", ".env"), "git rm --cached .env e confira o .gitignore")

    print("\n== Laboratório N: serviço do classificador ==")
    st, saude = pegar("http://localhost:8000/saude")
    if not checar("serviço respondendo em localhost:8000", st == 200,
                  "num terminal só para ele: uvicorn servico_classificador:app --host 0.0.0.0 --port 8000"):
        return
    checar("o serviço encontrou a chave do Gemini", bool(saude and saude.get("chave_configurada")),
           "configure GEMINI_API_KEY nos Secrets do Codespaces (ou no .env) e reinicie o serviço")
    st, _ = postar("http://localhost:8000/classificar", {"mensagem": "teste"})
    checar("sem token, o serviço recusa (401)", st == 401, f"resposta {st}: confira o SERVICO_TOKEN do serviço")

    print("\n== Laboratório N: três execuções, três rotas (URL de produção) ==")
    for rota in ("comercial", "suporte", "outros"):
        st, corpo = postar("http://localhost:5678/webhook/leads", LEADS_N[rota])
        obtida = corpo.get("rota") if isinstance(corpo, dict) else None
        checar(f"lead de {rota} → 201, rota {rota}", st == 201 and obtida == rota,
               f"resposta {st}, rota {obtida!r}: abra a execução em Executions e siga o item até o Switch")
    st, corpo = postar("http://localhost:5678/webhook/leads", LEADS_N["financeiro"])
    obtida = corpo.get("rota") if isinstance(corpo, dict) else None
    checar("variação 6.5: cobrança em dobro → rota financeiro", st == 201 and obtida == "financeiro",
           f"rota {obtida!r}: a regra financeiro precisa vir antes da regra revisão no Switch")
    print("   (os leads de teste ficam na tabela com origem = verificador; pode apagar as linhas depois)")

    rel = arq.relative_to(RAIZ).as_posix()
    checar(f"{rel} está no Git (commit feito)", rel in git("ls-files", "automacoes"),
           f"git add {rel} && git commit -m \"Liga o classificador à porta de entrada de leads\"")
    checar("commit enviado ao GitHub (push)", git("status", "-sb").find("ahead") == -1, "rode: git push")


def lab_o():
    print("\n== Laboratório O: quebre e conserte ==")
    arq, wf = achar("Porta de entrada de leads")
    if not checar("workflow “Porta de entrada de leads” exportado em automacoes/", wf is not None,
                  "rode: bash n8n/exportar.sh"):
        return
    _, alerta = achar("Alerta de falhas")
    checar("workflow “Alerta de falhas” exportado, com Error Trigger",
           alerta is not None and "errorTrigger" in tipos(alerta),
           "crie o workflow Alerta de falhas (Error Trigger → Montar alerta → Registrar falha) e exporte de novo")
    if alerta is not None:
        checar("Alerta de falhas publicado", alerta.get("active") is True,
               "sem Publish, o n8n não chama o workflow de alerta (a mensagem aparece no log do contêiner)")
    checar("a Porta de entrada aponta para o workflow de alerta (Settings › Error Workflow)",
           bool(wf.get("settings", {}).get("errorWorkflow")) and (alerta is None or wf["settings"]["errorWorkflow"] == alerta.get("id")),
           "no editor: menu … › Settings › Error Workflow: Alerta de falhas; salve, publique e exporte")
    nos = {n["name"]: n for n in wf.get("nodes", [])}
    cls = [n for n in wf.get("nodes", []) if n.get("type", "").endswith("httpRequest")
           and str(n.get("parameters", {}).get("url", "")).rstrip("/").endswith("/classificar")]
    if checar("o Classificar existe", bool(cls), "o nó HTTP Request que chama /classificar sumiu"):
        c = cls[0]
        checar("Classificar com Retry On Fail (2 tentativas ou mais)", c.get("retryOnFail") is True and int(c.get("maxTries", 3)) >= 2,
               "no nó: Settings › Retry On Fail ligado, Max Tries 3, Wait Between Tries 2000")
        checar("Classificar com saída de erro (On Error: Continue using error output)", c.get("onError") == "continueErrorOutput",
               "no nó: Settings › On Error › Continue (using error output)")
        saidas = wf.get("connections", {}).get(c["name"], {}).get("main", [])
        checar("a saída de erro do Classificar leva a um caminho de revisão", len(saidas) > 1 and bool(saidas[1]),
               "ligue a saída de erro ao Edit Fields “Sem classificação”, e dele ao Juntar")
    norm = nos.get("Normalizar", {}).get("parameters", {}).get("assignments", {}).get("assignments", [])
    nome = next((a.get("value", "") for a in norm if a.get("name") == "nome"), "")
    checar("o Normalizar aceita qualquer tipo de dado no nome (String)", "String(" in nome,
           "troque ($json.body.nome ?? '') por String($json.body.nome ?? '') no nome, no email, no curso e na mensagem")
    soltos = soltos_de(wf)
    checar("nenhum nó solto (todos conectados)", not soltos, f"nós sem conexão: {soltos}")
    checar("workflow publicado (Published)", wf.get("active") is True, "clique em Publish e exporte de novo")

    print("\n== Laboratório O: teste ao vivo ==")
    st, corpo = postar("http://localhost:5678/webhook/leads", {"nome": 42, "email": "teste.estranho@email.exemplo",
                       "origem": "verificador", "consentimento": True, "mensagem": "teste automático"})
    checar("dado inesperado (nome numérico) → 400, e não um lead sem nome", st == 400,
           f"resposta {st}: {str(corpo)[:100]}; confira o String() no Normalizar")
    servico_no_ar = pegar("http://localhost:8000/saude")[0] == 200
    if "--sem-servico" in sys.argv:
        if not checar("serviço parado, como pedido", not servico_no_ar, "pare o serviço (Ctrl+C no terminal dele) e rode de novo"):
            return
        st, corpo = postar("http://localhost:5678/webhook/leads", LEADS_N["comercial"])
        rota = corpo.get("rota") if isinstance(corpo, dict) else None
        checar("com o serviço parado, o lead vai para a revisão (201, rota revisao)", st == 201 and rota == "revisao",
               f"resposta {st}, rota {rota!r}: confira o Retry On Fail e a saída de erro do Classificar")
    else:
        if checar("serviço do classificador no ar", servico_no_ar, "suba o serviço, ou rode com --sem-servico para testar a falha"):
            st, corpo = postar("http://localhost:5678/webhook/leads", LEADS_N["comercial"])
            rota = corpo.get("rota") if isinstance(corpo, dict) else None
            checar("com o serviço no ar, o lead comercial segue para o comercial", st == 201 and rota == "comercial",
                   f"resposta {st}, rota {rota!r}")
            longa = dict(LEADS_N["comercial"], mensagem=("Quero saber as formas de pagamento do curso de Python. " * 45))
            st, corpo = postar("http://localhost:5678/webhook/leads", longa)
            rota = corpo.get("rota") if isinstance(corpo, dict) else None
            checar("variação 5.6: mensagem longa demais ainda é classificada (rota comercial)", st == 201 and rota == "comercial",
                   f"rota {rota!r}: o serviço recusa mensagens com mais de 2.000 caracteres (422); corte a mensagem no Normalizar")
        print("   (para testar o caminho de falha: pare o serviço e rode python verificar_n8n.py O --sem-servico)")

    diario = PASTA / "diario-de-falhas.md"
    texto = diario.read_text(encoding="utf-8") if diario.exists() else ""
    linhas = [l for l in texto.splitlines() if re.match(r"\|\s*[123]\s*\|", l)]
    checar("diário de falhas preenchido (3 falhas, sem “...”)", len(linhas) == 3 and not any("..." in l for l in linhas),
           "preencha automacoes/diario-de-falhas.md com o que aconteceu antes e depois de cada conserto")
    rel = arq.relative_to(RAIZ).as_posix()
    checar(f"{rel} está no Git (commit feito)", rel in git("ls-files", "automacoes"),
           "git add automacoes && git commit -m \"Fecha o Módulo 5: caminhos para quando algo dá errado\"")
    checar("commit enviado ao GitHub (push)", git("status", "-sb").find("ahead") == -1, "rode: git push")


LABS = {"L": lab_l, "M": lab_m, "N": lab_n, "O": lab_o}

if __name__ == "__main__":
    lab = next((a for a in sys.argv[1:] if not a.startswith("--")), "L").upper()
    if lab not in LABS:
        sys.exit(f"Laboratório desconhecido: {lab}. Opções: {', '.join(LABS)}")
    comum()
    LABS[lab]()
    print("\n" + ("Tudo certo! 🎉" if falhas == 0 else f"{falhas} checagem(ns) para revisar."))
    sys.exit(1 if falhas else 0)
