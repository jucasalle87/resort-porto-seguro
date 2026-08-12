"""
Persistência via GitHub Contents API — mesmo padrão usado nos outros
portais DarkPool (ex.: Fazenda Barra II).

Por que isso é necessário: o sistema de arquivos do Streamlit Cloud é
efêmero — qualquer coisa escrita localmente (config.yaml com os usuários,
access_log.csv) se perde quando o app reinicia ou é redeployado a partir do
GitHub. Gravando os dois arquivos no próprio repositório via API, eles
sobrevivem a restarts.

Configuração esperada em st.secrets (Settings > Secrets no Streamlit Cloud,
ou .streamlit/secrets.toml local):

    [github]
    token = "ghp_xxxxxxxxxxxxxxxxxxxx"
    repo = "seu-usuario/darkpool-resort-porto-seguro"
    branch = "main"

Sem esse secret configurado, todas as funções abaixo caem automaticamente
para leitura/escrita no arquivo local — funciona igual de ponta a ponta,
só não sobrevive a um redeploy no Streamlit Cloud.
"""

import base64
import os

import requests
import streamlit as st

TIMEOUT = 10


def _config():
    try:
        gh = st.secrets["github"]
        token = gh["token"]
        repo = gh["repo"]
        branch = gh.get("branch", "main")
        return token, repo, branch
    except (KeyError, FileNotFoundError):
        return None, None, None


def github_configurado() -> bool:
    token, repo, _ = _config()
    return bool(token and repo)


# --- fallback local (sem GitHub configurado) --------------------------------

def _ler_local(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _salvar_local(path: str, content: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# --- GitHub Contents API -----------------------------------------------

def ler_arquivo(path: str, default: str = "") -> str:
    """Lê o conteúdo (texto) de um arquivo. Se o GitHub estiver configurado,
    busca de lá primeiro (fonte da verdade); senão, lê do disco local."""
    token, repo, branch = _config()
    if not token:
        conteudo = _ler_local(path)
        return conteudo if conteudo is not None else default

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=TIMEOUT)
    except requests.RequestException as e:
        st.warning(f"Não foi possível conectar ao GitHub ({e}). Usando cópia local temporária.")
        conteudo = _ler_local(path)
        return conteudo if conteudo is not None else default

    if resp.status_code == 200:
        conteudo = base64.b64decode(resp.json()["content"]).decode("utf-8")
        # mantém uma cópia local também, útil se o GitHub cair momentaneamente
        _salvar_local(path, conteudo)
        return conteudo
    elif resp.status_code == 404:
        return default  # arquivo ainda não existe no repo — primeira execução
    else:
        st.warning(f"Não foi possível ler '{path}' no GitHub (status {resp.status_code}).")
        conteudo = _ler_local(path)
        return conteudo if conteudo is not None else default


def salvar_arquivo(path: str, content: str, mensagem: str = None):
    """Salva o conteúdo (texto) de um arquivo, tanto localmente quanto no
    GitHub (se configurado)."""
    _salvar_local(path, content)

    token, repo, branch = _config()
    if not token:
        return

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    # Precisa do sha do arquivo atual pra poder sobrescrever (regra da API do GitHub)
    sha = None
    try:
        resp = requests.get(url, headers=headers, params={"ref": branch}, timeout=TIMEOUT)
        if resp.status_code == 200:
            sha = resp.json()["sha"]
    except requests.RequestException:
        pass

    payload = {
        "message": mensagem or f"Atualiza {path}",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    try:
        put_resp = requests.put(url, headers=headers, json=payload, timeout=TIMEOUT)
        if put_resp.status_code not in (200, 201):
            st.warning(f"Não foi possível salvar '{path}' no GitHub (status {put_resp.status_code}).")
    except requests.RequestException as e:
        st.warning(f"Não foi possível conectar ao GitHub ({e}). '{path}' salvo só localmente.")
