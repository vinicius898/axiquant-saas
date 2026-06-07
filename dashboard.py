import streamlit as st
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from conexao_db import puxar_dados_nuvem, sincronizar_loja_shopify, sincronizar_facebook_ads
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
    st.session_state['usuario_email'] = ""

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# 3. TELA DE LOGIN
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("")
        st.title("🔒 AxiQuant Login")
        st.markdown("Insira suas credenciais para acessar o motor de inteligência.")
        
        email_input = st.text_input("E-mail corporativo")
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Acessar Painel", type="primary", use_container_width=True):
            with st.spinner("Autenticando..."):
                try:
                    resposta = supabase.auth.sign_in_with_password({
                        "email": email_input,
                        "password": senha_input
                    })
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_email'] = email_input 
                    st.rerun()
                except Exception as e:
                    st.error("Falha no login. Verifique seu e-mail e senha.")

# 4. PAINEL EXECUTIVO
else:
    st.title("📊 Painel de Inteligência Executiva")
    
    # BOTÃO 1: Robô Sincronizador Ativo da Shopify
    if st.sidebar.button("🛍️ Sincronizar Shopify"):
        with st.spinner("Varrendo API da Shopify e atualizando Supabase..."):
            sucesso, mensagem = sincronizar_loja_shopify(st.session_state['usuario_email'])
            if sucesso:
                st.sidebar.success(mensagem)
                st.toast("Dados da Shopify integrados!", icon="🛍️")
            else:
                st.sidebar.error(f"Erro: {mensagem}")
                
    st.sidebar.divider()

    # BOTÃO NEW: Robô Sincronizador do Facebook Ads
    if st.sidebar.button("🔵 Sincronizar Facebook Ads"):
        with st.spinner("Acessando servidores da Meta e cruzando investimentos..."):
            sucesso, mensagem = sincronizar_facebook_ads(st.session_state['usuario_email'])
            if sucesso:
                st.sidebar.success(mensagem)
                st.toast("Investimentos do Facebook Ads sincronizados!", icon="🔵")
            else:
                st.sidebar.error(f"Erro: {mensagem}")
                
    st.sidebar.divider()
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state['autenticado'] = False
        st.session_state['usuario_email'] = ""
        st.rerun()

    os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    cfo_agent = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        description="Você é um CFO sênior de um fundo quantitativo. Seja analítico e direto."
    )

    # BOTÃO PRINCIPAL: Motor de Análise e IA
    if st.sidebar.button("☁️ Sincronizar Operação", type="primary"):
        with st.spinner("Processando dados exclusivos da sua loja..."):
            
            dados = puxar_dados_nuvem(st.session_state['usuario_email']) 
            
            if dados is not None and len(dados) > 0:
                df = pd.DataFrame(dados)
                df['data'] = pd.to_datetime(df['data'])
                cols_numericas = ['leads', 'investimento_ads', 'ticket_medio', 'vendas_totais', 'churn', 'faturamento']
                for col in cols_numericas:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                df = df.sort_values('data').dropna()
                
                st.success(f"Mostrando dados isolados para a Empresa ID: {df['empresa_id'].iloc[0]}")
                
                # --- MATEMÁTICA DOS KPIs DE NEGÓCIO ---
                faturamento_total = df['faturamento'].sum()
                investimento_total = df['investimento_ads'].sum()
                vendas_totais = df['vendas_totais'].sum()
                leads_totais = df['leads'].sum()
                ticket_medio = df['ticket_medio'].mean()
                churn_medio = df['churn'].mean()
                
                roas = faturamento_total / investimento_total if investimento_total > 0 else 0
                cac = investimento_total / vendas_totais if vendas_totais > 0 else 0
                taxa_conversao = (vendas_totais / leads_totais) * 100 if leads_totais > 0 else 0

                st.markdown("### 📈 Raio-X Operacional e Financeiro")
                
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Faturamento Total", f"R$ {faturamento_total:,.2f}")
                kpi2.metric("ROAS (Retorno Ads)", f"{roas:.2f}x")
                kpi3.metric("CAC (Custo Aquisição)", f"R$ {cac:,.2f}")
                kpi4.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
                
                st.write("") 
                kpi5, kpi6, kpi7, kpi8 = st.columns(4)
                kpi5.metric("Vendas Totais", f"{int(vendas_totais)}")
                kpi6.metric("Leads Gerados", f"{int(leads_totais)}")
                kpi7.metric("Taxa de Conversão", f"{taxa_conversao:.2f}%")
                kpi8.metric("Churn Médio (Cancelamento)", f"{churn_medio:.2f}%")
                
                st.divider()

                # --- O CÉREBRO TRIPLO ---
                st.header("🧠 Motores de Machine Learning")
                tab1, tab2, tab3 = st.tabs(["Regressão (Causas)", "Classificação (Importância)", "Clusterização (Padrões)"])
                peso_ads = 0
                importancias_lista = ""

                with tab1:
                    try:
                        X_reg = sm.add_constant(df[['investimento_ads', 'leads', 'ticket_medio']])
                        modelo_ols = sm.OLS(df['faturamento'], X_reg).fit()
                        peso_ads = modelo_ols.params.get('investimento_ads', 0)
                        st.dataframe(pd.DataFrame({"Variável": modelo_ols.params.index, "Peso": modelo_ols.params.values}).style.format({"Peso": "{:.2f}"}))
                    except: pass

                with tab2:
                    try:
                        X_clf = df[['investimento_ads', 'leads', 'ticket_medio', 'churn']]
                        rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['faturamento'] > df['faturamento'].median()).astype(int))
                        importancias = pd.DataFrame({'Variável': X_clf.columns, 'Poder (%)': rf.feature_importances_ * 100}).sort_values('Poder (%)', ascending=False)
                        importancias_lista = importancias.to_dict('records')
                        st.bar_chart(importancias.set_index('Variável'))
                    except: pass

                with tab3:
                    try:
                        df['Cluster'] = KMeans(n_clusters=3, random_state=42).fit_predict(StandardScaler().fit_transform(df[['investimento_ads', 'faturamento', 'churn']])).astype(str)
                        st.scatter_chart(df, x='investimento_ads', y='faturamento', color='Cluster')
                    except: pass

                st.divider()
                st.subheader("🤖 Parecer do CFO Artificial")
                if cfo_agent:
                    with st.spinner("Analisando matrizes e métricas de negócio..."):
                        prompt_cfo = f"""
                        Dados globais: Faturamento R$ {faturamento_total:.2f}, Ads R$ {investimento_total:.2f}. 
                        Métricas Chave: ROAS de {roas:.2f}x, CAC de R$ {cac:.2f}, Conversão de {taxa_conversao:.2f}%, Churn de {churn_medio:.2f}%.
                        Motor Preditivo: O multiplicador Ads é {peso_ads:.2f}. Hierarquia sucesso: {importancias_lista}. 
                        Escreva um relatório executivo de 2 parágrafos.
                        """
                        st.write(cfo_agent.run(prompt_cfo).content)
            else:
                st.error("Nenhum dado encontrado para a sua loja.")
    else:
        st.info("👋 Motor pronto. Clique em Sincronizar na barra lateral.")
