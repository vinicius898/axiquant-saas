import streamlit as st
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from conexao_db import puxar_dados_nuvem
from agno.agent import Agent
from agno.models.groq import Groq
from supabase import create_client
import os

# 1. Configuração da Página e CSS
st.set_page_config(page_title="AxiQuant Admin", layout="wide", page_icon="💎")
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #1F2937;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# 2. Inicialização de Estado (Memória do Login)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Conexão com Supabase para Autenticação
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# 3. TELA DE LOGIN
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("")
        st.write("")
        st.title("🔒 AxiQuant Login")
        st.markdown("Insira suas credenciais para acessar o motor de inteligência.")
        
        email_input = st.text_input("E-mail corporativo")
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Acessar Painel", type="primary", use_container_width=True):
            with st.spinner("Autenticando..."):
                try:
                    # Tenta fazer o login no Supabase
                    resposta = supabase.auth.sign_in_with_password({
                        "email": email_input,
                        "password": senha_input
                    })
                    st.session_state['autenticado'] = True
                    st.rerun() # Recarrega a página para mostrar o painel
                except Exception as e:
                    st.error("Falha no login. Verifique seu e-mail e senha.")

# 4. PAINEL EXECUTIVO (Só aparece se autenticado)
else:
    st.title("📊 Painel de Inteligência Executiva (Cérebro Triplo)")
    st.markdown("Visão preditiva, prescritiva e descritiva alimentada por Machine Learning.")
    
    # Botão de Sair (Logout)
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state['autenticado'] = False
        st.rerun()

    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    cfo_agent = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        description="Você é um CFO sênior de um fundo quantitativo. Seja analítico e direto."
    )

    if st.sidebar.button("☁️ Sincronizar Operação", type="primary"):
        with st.spinner("Conectando ao banco de dados e rodando Machine Learning..."):
            dados = puxar_dados_nuvem()
            
            if dados is not None and len(dados) > 0:
                df = pd.DataFrame(dados)
                df['data'] = pd.to_datetime(df['data'])
                cols_numericas = ['leads', 'investimento_ads', 'ticket_medio', 'vendas_totais', 'churn', 'faturamento']
                for col in cols_numericas:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df = df.sort_values('data').dropna()
                
                st.success("Dados Sincronizados e Processados!")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Faturamento Total", f"R$ {df['faturamento'].sum():,.2f}")
                col2.metric("Investimento Total (Ads)", f"R$ {df['investimento_ads'].sum():,.2f}")
                col3.metric("Ticket Médio", f"R$ {df['ticket_medio'].mean():,.2f}")
                col4.metric("Dias Analisados", len(df))
                st.divider()

                st.header("🧠 Motores de Machine Learning")
                tab1, tab2, tab3 = st.tabs(["Regressão (Causas)", "Classificação (Importância)", "Clusterização (Padrões)"])
                peso_ads = 0
                importancias_lista = ""

                with tab1:
                    st.markdown("### 🔍 Regressão OLS")
                    try:
                        X_reg = df[['investimento_ads', 'leads', 'ticket_medio']]
                        y_reg = df['faturamento']
                        X_reg = sm.add_constant(X_reg)
                        modelo_ols = sm.OLS(y_reg, X_reg).fit()
                        peso_ads = modelo_ols.params.get('investimento_ads', 0)
                        st.dataframe(pd.DataFrame({"Variável": modelo_ols.params.index, "Peso": modelo_ols.params.values}).style.format({"Peso": "{:.2f}"}))
                        st.info(f"💡 **Insight:** Cada R$ 1,00 colocado em Ads gera um peso de {peso_ads:.2f} no faturamento.")
                    except Exception as e:
                        st.error(f"Erro OLS: {e}")

                with tab2:
                    st.markdown("### 🎯 Classificação")
                    try:
                        df['alta_performance'] = (df['faturamento'] > df['faturamento'].median()).astype(int)
                        X_clf = df[['investimento_ads', 'leads', 'ticket_medio', 'churn']]
                        rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, df['alta_performance'])
                        importancias = pd.DataFrame({'Variável': X_clf.columns, 'Poder (%)': rf.feature_importances_ * 100}).sort_values('Poder (%)', ascending=False)
                        importancias_lista = importancias.to_dict('records')
                        st.bar_chart(importancias.set_index('Variável'))
                    except Exception as e:
                        st.error(f"Erro Classificação: {e}")

                with tab3:
                    st.markdown("### 🧩 Clusterização")
                    try:
                        X_clust = df[['investimento_ads', 'faturamento', 'churn']]
                        df['Cluster'] = KMeans(n_clusters=3, random_state=42).fit_predict(StandardScaler().fit_transform(X_clust)).astype(str)
                        st.scatter_chart(df, x='investimento_ads', y='faturamento', color='Cluster')
                    except Exception as e:
                        st.error(f"Erro Cluster: {e}")

                st.divider()
                st.subheader("🤖 Parecer do CFO Artificial")
                if cfo_agent:
                    with st.spinner("Analisando matrizes matemáticas..."):
                        prompt_cfo = f"Dados globais de {len(df)} dias: Faturamento R$ {df['faturamento'].sum():.2f}, Ads R$ {df['investimento_ads'].sum():.2f}. Multiplicador Ads: {peso_ads:.2f}. Hierarquia sucesso: {importancias_lista}. Escreva relatório executivo de 2 parágrafos."
                        st.write(cfo_agent.run(prompt_cfo).content)
            else:
                st.error("Nenhum dado encontrado.")
    else:
        st.info("👋 Motor pronto. Clique em Sincronizar na barra lateral.")
