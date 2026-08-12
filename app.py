import os
import io
import csv
import time
from datetime import datetime, timedelta, timezone

import streamlit as st
import streamlit_authenticator as stauth
import yaml
import pandas as pd
from streamlit_autorefresh import st_autorefresh

import github_storage

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
LOG_PATH = os.path.join(BASE_DIR, "data", "access_log.csv")
ASSETS = os.path.join(BASE_DIR, "assets")
BRT = timezone(timedelta(hours=-3))

# Nomes dos arquivos DENTRO do repositório GitHub (caminho relativo, igual
# ao que aparece no repo — não usar caminho absoluto do disco local aqui).
GH_CONFIG_PATH = "config.yaml"
GH_LOG_PATH = "data/access_log.csv"
LOG_HEADER = ["timestamp_brt", "username", "nome", "email"]

st.set_page_config(
    page_title="Resort em Porto Seguro | DarkPool",
    page_icon="🏝️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# STYLE — paleta DarkPool
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    :root {
        --gold: #C9A96E; --gold-light: #E8D5B0; --gold-dark: #8B6A35;
        --forest: #1C2B1A; --forest-light: #4A7A47;
        --cream: #F5F0E8; --cream-dark: #EDE5D4;
        --ink: #1A1A18; --ink-mid: #3A3A36;
    }
    .stApp { background: var(--cream); }
    section[data-testid="stSidebar"] { background: var(--forest); }
    /* Só forçamos a cor clara em texto "solto" da sidebar (títulos, legendas,
       labels, markdown) — nunca em inputs/textareas ou em popovers/tooltips,
       que têm fundo claro próprio e ficariam ilegíveis (texto claro em
       fundo claro). */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] small {
        color: var(--cream);
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        color: var(--ink) !important;
        background: white !important;
        -webkit-text-fill-color: var(--ink) !important;
    }
    /* Botões da sidebar (Sair, Salvar, o expander de navegação) têm fundo
       claro por padrão — sem isso o texto ficava claro em fundo claro. */
    section[data-testid="stSidebar"] button {
        background: var(--gold) !important;
        border: 1px solid var(--gold) !important;
    }
    section[data-testid="stSidebar"] button p,
    section[data-testid="stSidebar"] button span,
    section[data-testid="stSidebar"] button div {
        color: var(--forest) !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] button:hover {
        background: var(--gold-light) !important;
        border-color: var(--gold-light) !important;
    }
    /* Cabeçalho do expander ("Navegação" etc.) tem o mesmo problema. */
    section[data-testid="stSidebar"] details summary {
        background: var(--gold) !important;
        border-radius: 4px;
    }
    section[data-testid="stSidebar"] details summary span,
    section[data-testid="stSidebar"] details summary p {
        color: var(--forest) !important;
        font-weight: 600 !important;
    }
    /* Qualquer tooltip/popover do Streamlit (ex: dica de senha) — sempre
       texto escuro em fundo claro, onde quer que seja renderizado. */
    div[data-baseweb="tooltip"], div[data-baseweb="popover"] {
        color: var(--ink) !important;
    }
    h1, h2, h3 { color: var(--forest); font-family: Georgia, 'Times New Roman', serif; }
    .dp-badge {
        display:inline-block; border:1px solid var(--gold); color:var(--gold-dark);
        font-size:11px; font-weight:600; letter-spacing:.14em; text-transform:uppercase;
        padding:4px 12px; margin-bottom:14px; border-radius:2px;
    }
    .dp-cover {
        position:relative; border-radius:6px; overflow:hidden; margin-bottom:8px;
    }
    .dp-cover img { width:100%; max-height:380px; object-fit:cover; filter:brightness(0.55); }
    .dp-cover-text {
        position:absolute; bottom:0; left:0; right:0; padding:28px 32px;
        color:white;
    }
    .dp-cover-text .eyebrow { color:var(--gold-light); font-size:12px; letter-spacing:.16em; text-transform:uppercase; margin-bottom:6px;}
    .dp-cover-text h1 { color:white; font-size:2.6rem; margin:0 0 4px 0; line-height:1.05; }
    .dp-cover-text .sub { color:var(--gold-light); font-style:italic; font-size:1.1rem; }
    .dp-section-label { font-size:11px; font-weight:700; letter-spacing:.16em; text-transform:uppercase; color:var(--gold-dark); margin-bottom:6px; }
    .dp-feature {
        background: var(--cream-dark); border-top:3px solid var(--gold); border-bottom:3px solid var(--gold);
        padding: 28px 30px; border-radius:4px; margin: 18px 0;
    }
    .dp-badge-feature {
        display:inline-block; background:var(--gold); color:var(--forest); font-size:10px; font-weight:700;
        letter-spacing:.14em; text-transform:uppercase; padding:5px 14px; margin-bottom:14px; border-radius:2px;
    }
    .dp-quote { border-left:4px solid var(--gold); padding-left:18px; font-style:italic; color:var(--forest); font-size:1.08rem; }
    .dp-chip {
        display:inline-block; border:1px solid var(--gold-dark); color:var(--gold-dark); font-size:12px;
        font-weight:500; padding:4px 11px; margin:3px 6px 3px 0; border-radius:2px;
    }
    .dp-contact-box {
        background: var(--forest); color: var(--cream); padding: 26px 30px; border-radius: 6px;
    }
    .dp-contact-box a { color: var(--gold-light) !important; text-decoration:none; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid var(--cream-dark); padding: 12px 8px; border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# HELPERS — leitura/escrita sempre passam pelo github_storage, que
# sincroniza com o repositório (se configurado) e cai para arquivo local
# como fallback. Isso resolve o problema de perder usuários/log quando o
# Streamlit Cloud reinicia o container.
# ─────────────────────────────────────────────────────────────
def load_config():
    conteudo = github_storage.ler_arquivo(GH_CONFIG_PATH)
    if not conteudo:
        # primeira execução sem GitHub configurado: usa o que já está local
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            conteudo = f.read()
    return yaml.safe_load(conteudo)


def save_config(config):
    conteudo = yaml.safe_dump(config, default_flow_style=False, allow_unicode=True)
    n_usuarios = len(config.get("credentials", {}).get("usernames", {}))
    github_storage.salvar_arquivo(
        GH_CONFIG_PATH, conteudo, mensagem=f"Atualiza usuários do dataroom ({n_usuarios} cadastrados)"
    )


def _log_rows_to_df(csv_text):
    if not csv_text or not csv_text.strip():
        return pd.DataFrame(columns=LOG_HEADER)
    try:
        return pd.read_csv(io.StringIO(csv_text))
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=LOG_HEADER)


def log_access(username, name, email):
    conteudo = github_storage.ler_arquivo(GH_LOG_PATH)
    df = _log_rows_to_df(conteudo)
    nova_linha = pd.DataFrame(
        [[datetime.now(BRT).strftime("%Y-%m-%d %H:%M:%S"), username, name, email]],
        columns=LOG_HEADER,
    )
    df = pd.concat([df, nova_linha], ignore_index=True)
    github_storage.salvar_arquivo(
        GH_LOG_PATH, df.to_csv(index=False), mensagem=f"Registra acesso de '{username}'"
    )


def read_log():
    conteudo = github_storage.ler_arquivo(GH_LOG_PATH)
    return _log_rows_to_df(conteudo)


def asset(name):
    return os.path.join(ASSETS, name)


def sync_config_from_github_to_local():
    """No arranque do app, garante que o config.yaml local (usado pelo
    streamlit_authenticator, que só sabe ler/escrever no disco) esteja
    atualizado com a última versão do GitHub."""
    if not github_storage.github_configurado():
        return
    conteudo = github_storage.ler_arquivo(GH_CONFIG_PATH)
    if conteudo:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(conteudo)


def push_local_config_to_github(mensagem="Atualiza config.yaml"):
    """Empurra o config.yaml local (que o streamlit_authenticator acabou de
    escrever, ex: após reset_password) de volta pro GitHub."""
    if not github_storage.github_configurado():
        return
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        conteudo = f.read()
    github_storage.salvar_arquivo(GH_CONFIG_PATH, conteudo, mensagem=mensagem)


# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────
sync_config_from_github_to_local()
config = load_config()


class SenhaLivreValidator(stauth.Validator):
    """Desliga a exigência de senha forte da biblioteca (maiúscula, número,
    caractere especial etc.) — aqui qualquer senha não vazia é aceita."""

    def validate_password(self, password: str) -> bool:
        return bool(password)


authenticator = stauth.Authenticate(
    credentials=CONFIG_PATH,
    cookie_name=config["cookie"]["name"],
    cookie_key=config["cookie"]["key"],
    cookie_expiry_days=config["cookie"]["expiry_days"],
    auto_hash=False,
    validator=SenhaLivreValidator(),
    # Sem exigência de senha forte — qualquer senha é aceita, e some a
    # dica de regras que aparecia embaixo do campo.
    password_instructions="",
)

if not st.session_state.get("authentication_status"):
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.image(asset("darkpool_logo.png"), width=140)
        st.markdown(
            "<div class='dp-badge'>Acesso Restrito · Estritamente Confidencial</div>",
            unsafe_allow_html=True,
        )
        st.markdown("### Dataroom — Resort em Porto Seguro")
        mensagem_pos_logout = st.session_state.pop("_mensagem_pos_logout", None)
        if mensagem_pos_logout:
            st.info(mensagem_pos_logout)
        authenticator.login(
            location="main",
            fields={
                "Form name": "Entrar",
                "Username": "Usuário",
                "Password": "Senha",
                "Login": "Entrar",
            },
        )
        if st.session_state.get("authentication_status") is False:
            st.error("Usuário ou senha incorretos.")
        elif st.session_state.get("authentication_status") is None:
            st.info("Informe seu usuário e senha para acessar o dataroom.")
        st.caption("Acesso individual e monitorado. Em caso de dúvidas, contate a DarkPool Intermediação de Ativos.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# LOGOUT AUTOMÁTICO POR INATIVIDADE (20 minutos)
# ─────────────────────────────────────────────────────────────
LIMITE_INATIVIDADE_MIN = 20

if "last_activity" not in st.session_state:
    st.session_state["last_activity"] = time.time()

# Verifica a cada 60s mesmo sem nenhuma ação do usuário (sem isso, o script
# só roda de novo quando alguém clica em algo, e o timeout nunca seria
# percebido enquanto a pessoa só fica olhando a tela sem clicar em nada).
st_autorefresh(interval=60_000, key="verifica_inatividade")

minutos_inativo = (time.time() - st.session_state["last_activity"]) / 60
if minutos_inativo > LIMITE_INATIVIDADE_MIN:
    authenticator.logout(location="unrendered")
    st.session_state.pop("_access_logged", None)
    st.session_state.pop("last_activity", None)
    st.session_state["_mensagem_pos_logout"] = (
        f"Sessão encerrada automaticamente após {LIMITE_INATIVIDADE_MIN} "
        "minutos de inatividade. Faça login novamente."
    )
    st.rerun()


def _marcar_atividade():
    st.session_state["last_activity"] = time.time()


# ─────────────────────────────────────────────────────────────
# LOGGED IN
# ─────────────────────────────────────────────────────────────
username = st.session_state["username"]
name = st.session_state["name"]
user_entry = config["credentials"]["usernames"].get(username, {})
email = user_entry.get("email", "")
role = user_entry.get("role", "user")

if not st.session_state.get("_access_logged"):
    log_access(username, name, email)
    st.session_state["_access_logged"] = True

with st.sidebar:
    st.image(asset("darkpool_logo.png"), width=110)
    st.markdown(f"**Bem-vindo(a),**  \n{name}")
    st.caption(f"Usuário: {username}")
    authenticator.logout("Sair", "sidebar")
    st.divider()
    page = "Dataroom"
    if role == "master":
        page = st.radio(
            "Navegação", ["Dataroom", "Administração"],
            label_visibility="collapsed", on_change=_marcar_atividade,
        )
    try:
        if authenticator.reset_password(
            username,
            location="sidebar",
            clear_on_submit=True,
            fields={
                "Form name": "Alterar Senha",
                "Current password": "Senha atual",
                "New password": "Nova senha",
                "Repeat password": "Confirmar nova senha",
                "Reset": "Salvar",
            },
        ):
            push_local_config_to_github(f"Atualiza senha de '{username}'")
            st.success("Senha alterada com sucesso.")
    except Exception as e:
        st.error(str(e))

# ═════════════════════════════════════════════════════════════
# ADMIN PAGE
# ═════════════════════════════════════════════════════════════
if role == "master" and page == "Administração":
    st.title("Administração do Dataroom")

    tab_users, tab_log = st.tabs(["👤 Usuários", "📋 Log de Acessos"])

    with tab_users:
        st.subheader("Cadastrar novo usuário")
        with st.form("add_user_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_username = c1.text_input("Usuário (login)")
            new_name = c2.text_input("Nome completo")
            new_email = c1.text_input("E-mail")
            new_password = c2.text_input("Senha provisória", type="password")
            submitted = st.form_submit_button("Cadastrar")

            if submitted:
                cfg = load_config()
                usernames = cfg["credentials"]["usernames"]
                if not new_username or not new_name or not new_password:
                    st.error("Preencha usuário, nome e senha.")
                elif new_username in usernames:
                    st.error("Já existe um usuário com esse login.")
                else:
                    usernames[new_username] = {
                        "name": new_name,
                        "email": new_email,
                        "password": stauth.Hasher.hash(new_password),
                        "role": "user",
                        "failed_login_attempts": 0,
                        "logged_in": False,
                    }
                    save_config(cfg)
                    st.success(f"Usuário '{new_username}' cadastrado com sucesso.")

        st.divider()
        st.subheader("Usuários com acesso")
        cfg = load_config()
        usernames = cfg["credentials"]["usernames"]

        removable = [u for u in usernames if usernames[u].get("role") != "master"]
        if removable:
            col_a, col_b = st.columns([3, 1])
            to_remove = col_a.selectbox("Remover acesso de:", removable)
            if col_b.button("Remover", type="primary"):
                cfg = load_config()
                cfg["credentials"]["usernames"].pop(to_remove, None)
                save_config(cfg)
                st.success(f"Acesso de '{to_remove}' removido.")
                cfg = load_config()
                usernames = cfg["credentials"]["usernames"]

        rows = [
            {"usuário": u, "nome": v.get("name", ""), "e-mail": v.get("email", ""), "papel": v.get("role", "user")}
            for u, v in usernames.items()
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with tab_log:
        st.subheader("Histórico de acessos")
        df = read_log()
        if df.empty:
            st.info("Nenhum acesso registrado ainda.")
        else:
            st.dataframe(df.sort_values("timestamp_brt", ascending=False), width="stretch", hide_index=True)
            st.download_button(
                "Baixar log (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                file_name="access_log_resort_porto_seguro.csv",
                mime="text/csv",
            )
        st.caption(
            "⚠️ Este log fica salvo no armazenamento do próprio app. Se o Streamlit Cloud reiniciar o "
            "container (por inatividade prolongada ou novo deploy via GitHub), o histórico pode ser perdido. "
            "Baixe o CSV periodicamente para manter um registro permanente."
        )

    st.stop()

# ═════════════════════════════════════════════════════════════
# DATAROOM — CONTEÚDO DO IMÓVEL
# ═════════════════════════════════════════════════════════════
import base64

def img_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <div class="dp-cover">
        <img src="data:image/jpeg;base64,{img_b64(asset('01.jpg'))}">
        <div class="dp-cover-text">
            <div class="eyebrow">Oportunidade de Investimento · Litoral Sul da Bahia</div>
            <h1>Resort em Porto Seguro</h1>
            <div class="sub">Praia do Mutá — Bahia</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor de Aquisição", "R$ 150 mi")
c2.metric("Apartamentos", "160 UHs")
c3.metric("Terreno", "53.000 m²")
c4.metric("Frente-Mar", "3.000 m²")

st.markdown("<div class='dp-section-label'>Sumário Executivo</div>", unsafe_allow_html=True)
st.markdown("## Hotel à beira-mar, pé na areia, em um dos destinos mais tradicionais da Bahia")
st.write(
    "Localizado na paradisíaca Praia do Mutá, em Porto Seguro (BA), este resort une um conceito único "
    "de hotel à beira-mar com arquitetura colonial baiana. O empreendimento está a apenas 15 km do "
    "Aeroporto Internacional de Porto Seguro."
)
st.write(
    "São 160 apartamentos standard (até 5 pessoas por unidade), distribuídos em um terreno de 53.000 m² "
    "com 10.000 m² de área construída e frente de mar exclusiva de 3.000 m² pé na areia — considerada uma "
    "das melhores praias de Porto Seguro."
)

st.divider()

st.markdown("<div class='dp-section-label'>Galeria de Fotos</div>", unsafe_allow_html=True)
st.markdown("## Conheça o Empreendimento")
gallery = [
    ("01.jpg", "Vista aérea do resort e da orla da Praia do Mutá"),
    ("02.jpg", "Vista aérea das quadras esportivas e piscinas"),
    ("06.jpg", "Piscina principal e estrutura gastronômica"),
    ("11.jpg", "Piscina ao entardecer"),
    ("12.jpg", "Frente de mar exclusiva — Praia do Mutá"),
    ("13.jpg", "Acesso privativo à praia"),
    ("03.jpg", "Fachada dos apartamentos entre coqueiros"),
    ("04.jpg", "Prédio de apartamentos com varandas"),
    ("05.jpg", "Alameda de coqueiros no jardim"),
    ("07.jpg", "Jardins e acesso aos apartamentos"),
    ("14.jpg", "Apartamento standard"),
    ("15.jpg", "Apartamento standard — configuração família"),
    ("08.jpg", "Lago de pesca exclusivo, com fauna preservada"),
    ("10.jpg", "Deck sobre o lago de pesca"),
    ("09.jpg", "Quadra de tênis"),
]
cols = st.columns(4)
for i, (fname, label) in enumerate(gallery):
    with cols[i % 4]:
        st.image(asset(fname), caption=label, width="stretch")

st.divider()

st.markdown("<div class='dp-section-label'>Vídeo de Apresentação</div>", unsafe_allow_html=True)
st.markdown("## Conheça o Resort em Vídeo")
st.video("https://youtu.be/dAATgLmdj-4")

st.divider()

st.markdown("<div class='dp-section-label'>Infraestrutura de Lazer & Entretenimento</div>", unsafe_allow_html=True)
st.markdown("## Complexo Completo de Lazer à Beira-Mar")
amenities = [
    ("1.000 Coqueiros", "Paisagismo exuberante em todo o resort."),
    ("5 Piscinas", "Distribuídas pelo resort, incluindo piscina à beira-mar."),
    ("10 Quadras de Tênis", "Estrutura completa para prática esportiva."),
    ("2 Quadras de Beach Tênis", "Recreação na areia, junto à orla."),
    ("Lago de Pesca Exclusivo", "Ambiente natural preservado, com fauna local."),
    ("Gastronomia na Praia", "Restaurante e bar servindo diretamente na areia."),
    ("Playground, Jogos & Convenções", "Lazer para toda a família e espaço para eventos corporativos."),
]
a_cols = st.columns(3)
for i, (title, desc) in enumerate(amenities):
    with a_cols[i % 3]:
        st.markdown(f"**{title}**")
        st.caption(desc)

st.divider()

st.markdown("<div class='dp-section-label'>Localização & Diferenciais Competitivos</div>", unsafe_allow_html=True)
st.markdown("## Praia do Mutá, Porto Seguro — Bahia")
st.write(
    "Localização privilegiada, pé na areia, em uma das melhores praias de Porto Seguro. A arquitetura "
    "rústica e colonial baiana está em harmonia com a natureza ao redor, atraindo turismo nacional e "
    "internacional para este destino turístico tradicional da Bahia."
)
chips = [
    "Praia do Mutá — Porto Seguro/BA", "15 km do Aeroporto Internacional",
    "Pé na Areia", "Arquitetura Colonial Baiana", "Integrado à Mata Atlântica",
]
st.markdown("".join(f"<span class='dp-chip'>{c}</span>" for c in chips), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── DESTAQUE: EXPANSÃO + PERFIL DO INVESTIMENTO ──
st.markdown('<div class="dp-feature">', unsafe_allow_html=True)
st.markdown('<div class="dp-badge-feature">Destaque do Investimento</div>', unsafe_allow_html=True)
st.markdown("<div class='dp-section-label'>Potencial de Expansão & Valorização</div>", unsafe_allow_html=True)
st.markdown("### Espaço para Crescimento Imediato")
st.write(
    "O terreno comporta a construção de mais de 200 novos apartamentos/suítes (50 m² cada), ampliando "
    "a capacidade do resort para captar a crescente demanda dos mercados de turismo de lazer, eventos "
    "corporativos e convenções."
)
e1, e2 = st.columns(2)
e1.metric("Novas Unidades Potenciais", "+200 UHs")
e2.metric("Área por Unidade Prevista", "50 m²")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='dp-section-label'>Perfil do Investimento</div>", unsafe_allow_html=True)
st.markdown("### Ativo Estratégico para Fundos, Redes Hoteleiras e Incorporadoras")
st.markdown(
    "<div class='dp-quote'>Excelente oportunidade para fundos imobiliários, redes hoteleiras, "
    "incorporadoras e investidores estratégicos. Trata-se de um ativo com elevado potencial de "
    "valorização imobiliária e rentabilidade recorrente, seja pela operação hoteleira atual, seja "
    "pela expansão do empreendimento em um destino consagrado: Porto Seguro — Bahia, Praia do Mutá.</div>",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── CONTATO ──
st.markdown(
    """
    <div class="dp-contact-box">
        <div class="dp-section-label" style="color:#E8D5B0;">Contato</div>
        <h3 style="color:white; margin-top:4px;">DarkPool Intermediação de Ativos</h3>
        <p style="color:#E8D5B0; font-style:italic;">Assessor Responsável</p>
        <p>📧 <a href="mailto:negocios@darkpool.com.br">negocios@darkpool.com.br</a></p>
        <p>💬 <a href="https://wa.me/554333369677" target="_blank">+55 43 3336-9677</a></p>
        <p>🌐 <a href="https://darkpool.com.br/" target="_blank">DarkPool.com.br</a></p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "Este documento é estritamente confidencial e foi preparado exclusivamente para fins informativos. "
    "As informações aqui contidas são baseadas em dados fornecidos pelo vendedor e não constituem "
    "auditoria ou due diligence. O destinatário não deverá reproduzir, distribuir ou utilizar este "
    "material sem autorização prévia por escrito da DarkPool Intermediação de Ativos."
)
