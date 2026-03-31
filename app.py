import streamlit as st

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------------------
st.set_page_config(
    page_title="Projetos em Python | Rodrigo Aiosa",
    page_icon="🐍",
    layout="wide"
)

# --------------------------------------------------
# FUNÇÕES INTERNAS (SUBSTITUI utils.py)
# --------------------------------------------------
def registrar_acesso(pagina):
    """Registro simples (evita erro em produção)"""
    # Pode evoluir depois (ex: banco, analytics)
    print(f"Acesso: {pagina}")

def exibir_rodape():
    """Rodapé padrão"""
    st.markdown("---")
    st.markdown(
        "<p style='text-align:center; color:#7b8ba8;'>© Rodrigo Aiosa</p>",
        unsafe_allow_html=True
    )

# --------------------------------------------------
# REGISTRO DE ACESSO
# --------------------------------------------------
registrar_acesso("Projetos Python")

# --------------------------------------------------
# FUNÇÃO PARA RENDER HTML
# --------------------------------------------------
def render_html(html: str):
    if html:
        st.markdown(html, unsafe_allow_html=True)

# --------------------------------------------------
# CACHE DE DADOS
# --------------------------------------------------
@st.cache_data
def get_projects():
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

# --------------------------------------------------
# COMPONENTE DE CARD
# --------------------------------------------------
def render_card(project):
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
# ESTILO
# --------------------------------------------------
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400&display=swap');

html, body, .main {
    background-color: #060912 !important;
}

.block-container {
    max-width: 1100px;
}

/* HERO */
.hero {
    text-align: center;
    margin-bottom: 50px;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    color: #f0f4ff;
}

.hero-sub {
    color: #7b8ba8;
}

/* INPUT */
div[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    color: white;
}

/* CARD */
.project-card {
    background: rgba(255,255,255,0.03);
    padding: 20px;
    border-radius: 16px;
    margin-bottom: 15px;
    transition: 0.3s;
}

.project-card:hover {
    transform: translateY(-3px);
}

.project-card-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.project-title {
    color: #e2e8f0;
    font-weight: bold;
}

.project-description {
    color: #7b8ba8;
    font-size: 0.9rem;
}

.project-btn {
    color: #00b4d8;
    text-decoration: none;
}
</style>
""")

# --------------------------------------------------
# HERO
# --------------------------------------------------
render_html("""
<div class="hero">
    <div class="hero-title">Aplicações que resolvem problemas reais</div>
    <div class="hero-sub">Automação • Dados • Inteligência</div>
</div>
""")

# --------------------------------------------------
# BUSCA
# --------------------------------------------------
search_query = st.text_input("", placeholder="🔍 Buscar projetos...")

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
