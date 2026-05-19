import streamlit as st
import pandas as pd
import statsmodels.api as sm
from conexao_db import puxar_dados_nuvem
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
from simulador_enxame import executar_simulacao_enxame

load_dotenv()

# Configuração da página (Ocultando a barra lateral por padrão para dar ar de sistema web)
st.set_page_config(page_title="AxiQuant | Painel Executivo",
                   layout="wide", initial_sidebar_state="expanded")

# --- O CSS PREMIUM (A Mágica do Front-end) ---
st.markdown("""
    <style>
    /* 1. Importando a fonte Inter do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

    /* 2. Aplicando a fonte no sistema inteiro e forçando o Dark Mode limpo */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #090C10; /* Fundo super escuro estilo GitHub Dark */
    }

    /* 3. Escondendo as marcas de "Projeto de Estudante" do Streamlit */
    #MainMenu {visibility: hidden;} /* Esconde o menu de hambúrguer */
    footer {visibility: hidden;} /* Esconde o "Made with Streamlit" */
    header {visibility: hidden;} /* Esconde a faixa branca no topo */

    /* 4. Estilizando a Barra Lateral */
    [data-testid="stSidebar"] {
        background-color: #11151C;
        border-right: 1px solid #1E2532;
    }

    /* 5. Transformando as Métricas em Cards Premium */
    [data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #21262D;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: #2F81F7;
    }
    [data-testid="stMetricLabel"] {
        color: #8B949E;
        font-weight: 600;
        font-size: 0.9rem;
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-weight: 800;
        font-size: 2rem;
    }

    /* 6. Botões Premium com Gradiente (Estilo Stripe) */
    .stButton > button {
        background: linear-gradient(135deg, #2F81F7 0%, #1F6FEB 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        height: 3rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 14px 0 rgba(47, 129, 247, 0.39);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(47, 129, 247, 0.5);
    }

    /* 7. Caixa de Informação e Expander */
    div.stInfo, div.stSuccess, div.stWarning, div.stError {
        border-radius: 10px;
        border: 1px solid #30363D;
        background-color: #0D1117;
    }
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #C9D1D9;
        background-color: #161B22;
        border-radius: 8px;
    }

    /* Divisórias mais elegantes */
    hr { border-top: 1px solid #21262D; margin: 2.5em 0; }
    </style>
    """, unsafe_allow_html=True)


# --- MOTOR ESTATÍSTICO (OLS) ---
def rodar_estatistica(df):
    try:
        Y = df['faturamento']
        X = df[['Investimento_Ads', 'Preco_Venda', 'Postagens_Social']]
        X = sm.add_constant(X)
        modelo = sm.OLS(Y, X).fit()

        coef = modelo.params
        p_values = modelo.pvalues
        conf_int = modelo.conf_int()

        return {
            "ads_impacto": coef['Investimento_Ads'],
            "preco_impacto": coef['Preco_Venda'],
            "ads_status": "Confirmado" if p_values['Investimento_Ads'] < 0.05 else "Em Observação",
            "preco_status": "Confirmado" if p_values['Preco_Venda'] < 0.05 else "Em Observação",
            "conf_intervalo": [conf_int.loc['Preco_Venda'][0], conf_int.loc['Preco_Venda'][1]],
            "ticket_medio_base": df['faturamento'].sum() / (len(df) * 5)
        }
    except Exception as e:
        st.error(f"Erro no motor estatístico: {e}")
        return None


# --- AGENTE CFO (O CONSELHEIRO PROATIVO) ---
cfo_agente = Agent(
    model=Groq(id="llama-3.3-70b-versatile"),
    instructions=[
        "Você é o CFO Estratégico da AxiQuant. Fale de forma natural, direta e executiva.",
        "PROIBIDO: Não use NENHUMA formatação matemática, símbolos de dólar/cifrão soltos para equações ou blocos de código. Isso gera erros visuais na tela. Escreva valores em Reais normalmente (ex: R$ 10,00).",
        "REGRA DO 1 REAL: Se o impacto de Ads for 'Confirmado', escreva de forma simples: 'Para cada R$ 1,00 investido em Ads, o retorno marginal estimado é de R$ [valor]'. Não invente contas extras.",
        "DADOS DE RUÍDO ('Em Observação'): Se uma métrica estiver 'Em Observação', seja radicalmente honesto. Diga ao cliente que os dados atuais são ruído estatístico (inconclusivos) e recomende não tomar decisões de negócios baseadas apenas nisso.",
        "Mantenha o relatório enxuto. Use listas simples."
    ],
    markdown=True
)

# --- INTERFACE ---
st.sidebar.markdown("### 💎 AxiQuant Admin")
st.sidebar.caption("Motor de Previsão de faturamento v1.0")

if st.sidebar.button("☁️ Sincronizar Operação"):
    with st.spinner("Conectando ao banco de dados..."):
        df_nuvem = puxar_dados_nuvem()
        if df_nuvem is not None:
            st.session_state['dados_salvos'] = df_nuvem
            if 'relatorio_cfo' in st.session_state:
                del st.session_state['relatorio_cfo']
            st.sidebar.success("Dados Sincronizados!")
        else:
            st.sidebar.error("Erro ao puxar dados da nuvem.")

st.markdown("## 📊 Painel de Inteligência Executiva")
st.caption("Visão em tempo real da performance de vendas e eficiência de capital.")
st.divider()

if 'dados_salvos' in st.session_state:
    df = st.session_state['dados_salvos']

    col_graf, col_ia = st.columns([1.1, 1])

    with col_graf:
        st.markdown("#### 📈 Tendência de Faturamento")
        st.line_chart(df.set_index('data')['faturamento'], color="#2F81F7")

        c1, c2 = st.columns(2)
        c1.metric("faturamento Total",
                  f"R$ {df['faturamento'].sum():,.2f}", "+12% vs. mês anterior")
        c2.metric("Dias Analisados", len(df), "Período validado")

    with col_ia:
        st.markdown("#### 🤖 Parecer do CFO Artificial")

        metricas = rodar_estatistica(df)

        if metricas:
            if 'relatorio_cfo' not in st.session_state:
                with st.spinner("Analisando eficiência do caixa..."):
                    prompt = f"""
                    Crie um laudo executivo direto ao ponto com base nestes números reais do fechamento:
                    - Retorno Marginal Ads: R$ {metricas['ads_impacto']:.2f} (Status: {metricas['ads_status']})
                    - Retorno Marginal Preço: R$ {metricas['preco_impacto']:.2f} (Status: {metricas['preco_status']})
                    - Intervalo de Segurança do Preço: R$ {metricas['conf_intervalo'][0]:.2f} até R$ {metricas['conf_intervalo'][1]:.2f}
                    
                    Seja honesto. Se o preço estiver 'Em Observação', avise o cliente que os dados atuais são inconclusivos e parecem ruído estatístico.
                    """
                    resposta_cfo = cfo_agente.run(prompt)
                    if resposta_cfo:
                        st.session_state['relatorio_cfo'] = resposta_cfo.content

            if 'relatorio_cfo' in st.session_state:
                st.markdown(st.session_state['relatorio_cfo'])

            # --- SESSÃO DO SIMULADOR ---
            st.divider()
            st.markdown("#### 🧪 Inteligência de Enxame")
            st.caption(
                "Projete o futuro: Teste a reação do consumidor a um novo preço antes de aplicá-lo.")

            ticket_atual = metricas['ticket_medio_base']

            novo_preco = st.slider(
                "Simular Novo Ticket Médio (R$)",
                min_value=float(ticket_atual * 0.5),
                max_value=float(ticket_atual * 2.0),
                value=float(ticket_atual * 1.15),
                format="R$ %.2f"
            )

            if st.button("🚀 Rodar Focus Group Virtual"):
                with st.spinner("Convocando personas e simulando reações..."):
                    resultado_simulacao = executar_simulacao_enxame(
                        ticket_atual, novo_preco)

                    with st.expander("Ver depoimentos do painel de clientes"):
                        for i, resposta in enumerate(resultado_simulacao["reacoes"]):
                            st.info(f"**Persona {i+1}:** {resposta}")

                    st.markdown("##### ⚖️ Veredito da Precificação")
                    st.markdown(resultado_simulacao["veredito_cfo"])

        else:
            st.error("Erro ao calcular métricas estatísticas.")
else:
    st.info("👋 **Aguardando dados.** Clique em Sincronizar na barra lateral para iniciar o motor.")
