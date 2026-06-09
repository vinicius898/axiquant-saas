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

# 3. TELA DE ACESSO (LOGIN / CADASTRO)
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("")
        st.title("💎 AxiQuant SaaS")
        st.markdown("O cérebro financeiro do seu e-commerce.")
        
        tab_login, tab_cadastro = st.tabs(["🔒 Já tenho conta", "✨ Criar minha conta"])
        
        with tab_login:
            email_login = st.text_input("E-mail corporativo", key="log_email")
            senha_login = st.text_input("Senha", type="password", key="log_senha")
            
            if st.button("Acessar Painel", type="primary", use_container_width=True):
                with st.spinner("Autenticando..."):
                    try:
                        resposta = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                        st.session_state['autenticado'] = True
                        st.session_state['usuario_email'] = email_login 
                        st.rerun()
                    except Exception as e:
                        st.error("Falha no login. Verifique seu e-mail e senha.")
                        
        with tab_cadastro:
            email_cad = st.text_input("Seu E-mail", key="cad_email")
            senha_cad = st.text_input("Crie uma Senha (mínimo 6 caracteres)", type="password", key="cad_senha")
            
            if st.button("Criar Conta Grátis", type="primary", use_container_width=True):
                with st.spinner("Preparando seu cofre de dados..."):
                    try:
                        resposta = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                        st.success("Conta criada com sucesso! Vá na aba 'Já tenho conta' e faça seu primeiro login.")
                    except Exception as e:
                        st.error(f"O Supabase relatou o seguinte erro: {e}")

# 4. ÁREA LOGADA (ONBOARDING OU PAINEL)
else:
    # Verifica se a empresa existe no banco; se não, cria na hora (A mágica do SaaS)
    empresa_resp = supabase.table('empresas').select('*').eq('email_dono', st.session_state['usuario_email']).execute()
    if not empresa_resp.data:
        supabase.table('empresas').insert({"email_dono": st.session_state['usuario_email']}).execute()
        empresa_resp = supabase.table('empresas').select('*').eq('email_dono', st.session_state['usuario_email']).execute()
    
    empresa = empresa_resp.data[0]
    
    # 4.1 TELA DE ONBOARDING (Se estiver faltando alguma chave)
    if not empresa.get('shopify_token') or not empresa.get('meta_token'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🚀 Bem-vindo ao AxiQuant!")
            st.info("Para ativarmos o seu CFO Artificial, precisamos conectar a sua operação.")
            
            with st.form("form_integracao"):
                st.write("### 🛍️ Integração Shopify")
                shop_url = st.text_input("URL da Loja", placeholder="ex: sua-loja.myshopify.com")
                shop_token = st.text_input("Token da API do Admin", placeholder="shpat_...", type="password")
                
                st.write("### 🔵 Integração Facebook Ads")
                meta_id = st.text_input("ID da Conta de Anúncios", placeholder="act_123456789")
                meta_token = st.text_input("Token de Acesso (Graph API)", placeholder="EAA...", type="password")
                
                if st.form_submit_button("Salvar Chaves e Ativar Painel", type="primary", use_container_width=True):
                    if shop_url and shop_token and meta_id and meta_token:
                        supabase.table('empresas').update({
                            "shopify_url": shop_url.replace("https://", ""),
                            "shopify_token": shop_token,
                            "meta_account_id": meta_id,
                            "meta_token": meta_token
                        }).eq('email_dono', st.session_state['usuario_email']).execute()
                        st.success("Tudo certo! Redirecionando para o painel...")
                        st.rerun()
                    else:
                        st.warning("Por favor, preencha todos os campos para continuar.")
                        
        if st.sidebar.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.session_state['usuario_email'] = ""
            st.rerun()
            
    # 4.2 O PAINEL EXECUTIVO PRINCIPAL (Se as chaves estiverem configuradas)
    else:
        st.title("📊 Painel de Inteligência Executiva")
        
        if st.sidebar.button("🛍️ Sincronizar Shopify"):
            with st.spinner("Varrendo API da Shopify e atualizando Supabase..."):
                sucesso, mensagem = sincronizar_loja_shopify(st.session_state['usuario_email'])
                if sucesso:
                    st.sidebar.success(mensagem)
                    st.toast("Dados da Shopify integrados!", icon="🛍️")
                else:
                    st.sidebar.error(f"Erro: {mensagem}")
                    
        st.sidebar.divider()

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
                            prompt_cfo = f"Dados: Fat R${faturamento_total:.2f}, Ads R${investimento_total:.2f}, ROAS {roas:.2f}x, CAC R${cac:.2f}, Conv {taxa_conversao:.2f}%. Motor Preditivo Ads peso {peso_ads:.2f}. Hierarquia: {importancias_lista}. Escreva relatório executivo em 2 parágrafos."
                            st.write(cfo_agent.run(prompt_cfo).content)
                else:
                    st.info("O seu cofre está vazio. Clique em Sincronizar Shopify e depois Sincronizar Facebook Ads na barra lateral.")
        else:
            st.info("👋 Seja muito bem-vindo! Clique em Sincronizar na barra lateral para dar a partida nos motores.")
