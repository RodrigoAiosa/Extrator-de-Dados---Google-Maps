import streamlit as st
from utils import exibir_rodape, registrar_acesso

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (SEMPRE NO TOPO)
# --------------------------------------------------
st.set_page_config(
    page_title="Projetos em Python | Rodrigo Aiosa",
    page_icon="🐍",
    layout="wide"
)

# --------------------------------------------------
# REGISTRO DE ACESSO
# --------------------------------------------------
registrar_acesso("Projetos Python")

# --------------------------------------------------
# FUNÇÕES UTILITÁRIAS
# --------------------------------------------------
def render_html(html: str):
    """Render seguro de HTML"""
    if html:
        st.markdown(html, unsafe_allow_html=True)

@st.cache_data
def get_projects():
    """Cache dos projetos (escalável)"""
    return [
        {
            "title": "🎓 Simulador ENEM",
            "desc": "Simulador completo gratuito com análise de desempenho",
            "url": "https://enem-simulador.streamlit.app/"
        },
        {
            "title": "🚀 BI Data Generator",
            "desc": "Ferramenta de análise inteligente com insights automáticos",
            "url": "https://ai-bidatagenerator.streamlit.app/"
        },
        {
            "title": "📍 Extrator Google Maps",
            "desc": "Geração de leads estruturados a partir de dados públicos",
            "url": "https://extrator-de-dados-gm.streamlit.app/"
        }
    ]

def render_card(project):
    """Componente reutilizável de card"""
    html = f"""
    <div class="project-card">
        <div class="project-card-inner">
            <div>
                <div class="project-title">{project['title']}</div>
                <div class="project-description">{project['desc']}</div>
            </div>
            <div>
                <a href="{project['url']}" target="_blank" class="project-btn">
                    Acessar →
                </a>
            </div>
        </div>
    </div>
    """
    render_html(html)

# --------------------------------------------------
# ESTILO GLOBAL (UI MODERNA)
# --------------------------------------------------
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, .main, [data-testid="stAppViewContainer"] {
    background-color: #060912 !important;
}

/* CONTAINER */
.block-container {
    max-width: 1200px !important;
    padding: 3rem !important;
}

/* HERO */
.hero {
    text-align: center;
    margin-bottom: 60px;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    color: #f0f4ff;
}

.hero-sub {
    color: #7b8ba8;
    margin-top: 10px;
}

/* INPUT */
div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(0,180,216,0.3) !important;
    color: #fff !important;
}

/* CARD */
.project-card {
    background: rgba(255,255,255,0.03);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid rgba(255,255,255,0.05);
    transition: 0.3s;
}

.project-card:hover {
    transform: translateY(-3px);
    border-color: rgba(0,180,216,0.5);
}

.project-card-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.project-title {
    font-weight: 700;
    color: #e2e8f0;
}

.project-description {
    font-size: 0.9rem;
    color: #7b8ba8;
}

/* BOTÃO */
.project-btn {
    padding: 10px 16px;
    border-radius: 10px;
    text-decoration: none;
    color: #00b4d8;
    border: 1px solid rgba(0,180,216,0.3);
}

.project-btn:hover {
    background: rgba(0,180,216,0.1);
}
</style>
""")

# --------------------------------------------------
# HERO
# --------------------------------------------------
render_html("""
<div class="hero">
    <div class="hero-title">Aplicações que resolvem problemas reais</div>
    <div class="hero-sub">
        Automação • Dados • Inteligência aplicada
    </div>
</div>
""")

# --------------------------------------------------
# BUSCA
# --------------------------------------------------
search_query = st.text_input(
    "",
    placeholder="🔍 Buscar projetos..."
)

# --------------------------------------------------
# DADOS
# --------------------------------------------------
projects = get_projects()

# --------------------------------------------------
# FILTRO
# --------------------------------------------------
if search_query:
    filtered = [
        p for p in projects
        if search_query.lower() in p["title"].lower()
        or search_query.lower() in p["desc"].lower()
    ]
else:
    filtered = projects

# --------------------------------------------------
# RESULTADOS
# --------------------------------------------------
st.markdown("### 📊 Resultados")

if not filtered:
    render_html("""
    <div style="text-align:center; padding:40px; color:#7b8ba8;">
        Nenhum projeto encontrado
    </div>
    """)
else:
    for project in filtered:
        render_card(project)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
exibir_rodape()
