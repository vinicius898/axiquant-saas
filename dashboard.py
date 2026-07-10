import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.ensemble import RandomForestClassifier
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV, Ridge
import xgboost as xgb
import plotly.express as px
from conexao_db import puxar_dados_nuvem, sincronizar_loja_shopify, sincronizar_facebook_ads
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from supabase import create_client
from openai import OpenAI

# 1. Configuração da Página
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

# 2. Inicialização
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
    st.session_state['usuario_email'] = ""
if 'dados_carregados' not in st.session_state:
    st.session_state['dados_carregados'] = False
if 'dados_loja' not in st.session_state:
    st.session_state['dados_loja'] = None

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
STRIPE_LINK = "https://buy.stripe.com/test_dRm4gy9uy5xC7y7bPDdAk00"

# 3. TELA DE ACESSO
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.write("")
        st.title("💎 AxiQuant SaaS")
        st.markdown("O cérebro financeiro das suas campanhas.")
        
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
                    except Exception:
                        st.error("Falha no login. Verifique seu e-mail e senha.")
                        
        with tab_cadastro:
            email_cad = st.text_input("Seu E-mail", key="cad_email")
            senha_cad = st.text_input("Crie uma Senha", type="password", key="cad_senha")
            if st.button("Criar Conta Grátis", type="primary", use_container_width=True):
                with st.spinner("Preparando cofre..."):
                    try:
                        resposta = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                        st.success("Conta criada! Acesse na aba ao lado.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

# 4. ÁREA LOGADA
else:
    parametros_url = st.query_params
    retorno_pagamento = parametros_url.get("pagamento", None)
    
    empresa_resp = supabase.table('empresas').select('*').eq('email_dono', st.session_state['usuario_email']).execute()
    if not empresa_resp.data:
        if retorno_pagamento == "aprovado":
            supabase.table('empresas').insert({"email_dono": st.session_state['usuario_email'], "assinatura_ativa": True}).execute()
        else:
            supabase.table('empresas').insert({"email_dono": st.session_state['usuario_email']}).execute()
        empresa_resp = supabase.table('empresas').select('*').eq('email_dono', st.session_state['usuario_email']).execute()
    
    empresa = empresa_resp.data[0]
    
    if retorno_pagamento == "aprovado" and not empresa.get('assinatura_ativa', False):
        supabase.table('empresas').update({"assinatura_ativa": True}).eq('email_dono', st.session_state['usuario_email']).execute()
        empresa['assinatura_ativa'] = True
        st.toast("Pagamento Identificado!", icon="🎉")

    assinatura_ativa = empresa.get('assinatura_ativa', False)
    agora = pd.Timestamp.utcnow()
    trial_valido = False
    
    if empresa.get('data_expiracao_trial'):
        expiracao = pd.to_datetime(empresa['data_expiracao_trial'], utc=True)
        if (expiracao - agora).days >= 0:
            trial_valido = True

    tem_acesso = assinatura_ativa or trial_valido

    if not tem_acesso:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔒 Período de teste finalizado")
            st.markdown("### Plano AxiQuant Pro — R$ 57,00/mês")
            st.link_button("💳 Assinar via Stripe", STRIPE_LINK, type="primary", use_container_width=True)
            if st.button("Sair da Conta"):
                st.session_state['autenticado'] = False
                st.rerun()

    elif not empresa.get('shopify_token') or not empresa.get('meta_token'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🚀 Bem-vindo ao AxiQuant!")
            with st.form("form_integracao"):
                shop_url = st.text_input("URL Shopify (Opcional)")
                shop_token = st.text_input("Token Shopify (Opcional)", type="password")
                meta_id = st.text_input("ID Meta Ads")
                meta_token = st.text_input("Token Meta", type="password")
                if st.form_submit_button("Salvar Chaves", type="primary", use_container_width=True):
                    supabase.table('empresas').update({"shopify_url": shop_url.replace("https://", ""), "shopify_token": shop_token, "meta_account_id": meta_id, "meta_token": meta_token}).eq('email_dono', st.session_state['usuario_email']).execute()
                    st.rerun()

    else:
        st.title("📊 Avaliação de Performance de Campanhas (ROI)")
        
        if st.sidebar.button("🛍️ Puxar Dados Externos (API)"):
            sucesso, msg = sincronizar_facebook_ads(st.session_state['usuario_email'])
            if sucesso: st.toast("Dados atualizados!")
            else: st.sidebar.error(msg)
        
        if st.sidebar.button("🚪 Sair"):
            st.session_state['autenticado'] = False
            st.session_state['dados_carregados'] = False
            st.rerun()

        # Agente CFO configurado para consultoria de Tráfego/Marketing
        groq_client = OpenAI(
            api_key=st.secrets.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1"
        )
        
        cfo_agent = Agent(
            model=OpenAIChat(id="llama-3.3-70b-versatile", client=groq_client),
            description="Você é um consultor financeiro focado em ajudar donos de e-commerce a otimizarem campanhas de marketing. Use linguagem simples e direta."
        )

        if st.sidebar.button("☁️ Sincronizar Painel", type="primary"):
            with st.spinner("Processando histórico de campanhas..."):
                dados = puxar_dados_nuvem(st.session_state['usuario_email'])
                if dados:
                    st.session_state['dados_loja'] = dados
                    st.session_state['dados_carregados'] = True
                    if "relatorio_gerado" in st.session_state: del st.session_state["relatorio_gerado"]
                    if "plano_acao_gerado" in st.session_state: del st.session_state["plano_acao_gerado"]
                    st.rerun()

        if st.session_state['dados_carregados'] and st.session_state['dados_loja']:
            df = pd.DataFrame(st.session_state['dados_loja'])
            
            # Limpeza das métricas numéricas
            colunas_numericas = ['investimento_ads', 'faturamento', 'alcance_organico', 'interacoes_engajamento']
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Cada linha é tratada como uma campanha independente
            csv_export = df.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="📥 Exportar Campanhas (CSV)",
                data=csv_export,
                file_name="axiquant_campanhas.csv",
                mime="text/csv"
            )
            
            # MCM = Receita gerada pela campanha - Custo da campanha
            df['mcm'] = df['faturamento'] - df['investimento_ads']
            
            fat_total = df['faturamento'].sum()
            inv_total = df['investimento_ads'].sum()
            mcm_total = df['mcm'].sum()
            margem_exibida = (mcm_total / fat_total) * 100 if fat_total > 0 else 0
            
            alcance_total = df['alcance_organico'].sum()
            engajamento_total = df['interacoes_engajamento'].sum()
            qtd_campanhas = len(df)
            
            st.markdown("### 🎯 Visão Geral das Campanhas")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Receita (Atribuída)", f"R$ {fat_total:,.2f}", help="Total em Vendas gerado diretamente pelos anúncios.")
            kpi2.metric("Lucro Direto (MCM)", f"R$ {mcm_total:,.2f}", delta=f"{margem_exibida:.1f}% Margem")
            kpi3.metric("Alcance Total (Views)", f"{int(alcance_total):,}".replace(",", "."))
            kpi4.metric("Campanhas Analisadas", f"{qtd_campanhas}")
            st.sidebar.metric("Custo Total (Ads)", f"R$ {inv_total:,.2f}")
            st.divider()

            st.header("🧠 Inteligência Artificial Aplicada")
            tab1, tab2, tab3, tab4 = st.tabs(["💸 Atribuição de Lucro", "🎯 Variáveis de Peso", "🚥 Clusterização (GMM)", "🔮 Simulador XGBoost"])
            
            peso_org = 0
            
            with tab1:
                st.subheader("Atribuição de Receita e Correção de Multicolinearidade")
                st.write("O modelo avalia se os gastos em anúncios e o alcance orgânico estão se canibalizando. Se detectado, a IA aplica correções automáticas.")
                
                try:
                    features = ['investimento_ads', 'alcance_organico']
                    X = df[features]
                    y = df['mcm']
                    
                    # 1. Diagnóstico Formal de Multicolinearidade (VIF)
                    X_vif_with_const = sm.add_constant(X)
                    vif_data = pd.DataFrame()
                    vif_data["Variável"] = X_vif_with_const.columns
                    vif_data["VIF"] = [variance_inflation_factor(X_vif_with_const.values, i) for i in range(X_vif_with_const.shape[1])]
                    
                    tem_multicolinearidade = (vif_data.loc[vif_data["Variável"] != "const", "VIF"] > 5).any()
                    
                    with st.expander("📊 Ver Diagnóstico Estatístico de Multicolinearidade (VIF)"):
                        st.dataframe(vif_data)
                        if tem_multicolinearidade:
                            st.warning("⚠️ Multicolinearidade detectada (VIF > 5). OLS padrão não é confiável.")
                        else:
                            st.success("✅ Variáveis independentes saudáveis (VIF < 5).")

                    if tem_multicolinearidade:
                        # 2. Se houver problema, usamos RidgeCV com Validação Cruzada (Critério Científico)
                        scaler_X = StandardScaler()
                        scaler_y = StandardScaler()
                        
                        X_scaled = scaler_X.fit_transform(X)
                        y_scaled = scaler_y.fit_transform(y.values.reshape(-1, 1)).flatten()
                        
                        alphas_grid = np.logspace(-3, 3, 50)
                        ridge_cv = RidgeCV(alphas=alphas_grid, store_cv_values=False)
                        ridge_cv.fit(X_scaled, y_scaled)
                        
                        std_X = scaler_X.scale_
                        std_y = scaler_y.scale_[0]
                        coef_originais = ridge_cv.coef_ * (std_y / std_X)
                        intercepto = scaler_y.mean_[0] - np.sum(coef_originais * scaler_X.mean_)
                        
                        peso_ads = coef_originais[0]
                        peso_org = coef_originais[1]
                        
                        st.info(f"🛡️ **Modelo Ridge Aplicado:** O sistema ajustou os pesos matematicamente via Validação Cruzada (Alpha Ótimo: {ridge_cv.alpha_:.2f}).")
                    
                    else:
                        # Se os dados passarem no teste do VIF, usa OLS puro
                        X_ols = sm.add_constant(X)
                        modelo_ols = sm.OLS(y, X_ols).fit()
                        
                        peso_ads = modelo_ols.params.get('investimento_ads', 0)
                        peso_org = modelo_ols.params.get('alcance_organico', 0)
                        intercepto = modelo_ols.params.get('const', 0)
                        
                        st.info("📉 **Modelo OLS Aplicado:** Dados sem multicolinearidade severa detectada.")

                    st.success(f"💡 **Conclusão:** Cada visualização da campanha gera em média **R$ {peso_org:.4f}** adicionais. Enquanto isso, cada R$ 1,00 colocado em Anúncios retorna **R$ {peso_ads:.2f}** de lucro incremental.")
                    
                    df_coefs = pd.DataFrame({
                        "Métrica Operacional": ["Receita de Inércia (Intercepto)", "Tráfego Pago (R$ Investido)", "Alcance (Views)"],
                        "Impacto Direto no Lucro (R$)": [intercepto, peso_ads, peso_org]
                    })
                    st.dataframe(df_coefs.style.format({"Impacto Direto no Lucro (R$)": "{:,.4f}"}), use_container_width=True)
                
                except Exception as e: 
                    st.warning(f"Erro ao computar matriz: {e}")

            with tab2:
                try:
                    X_clf = df[['investimento_ads', 'alcance_organico', 'interacoes_engajamento']]
                    rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['mcm'] > df['mcm'].median()).astype(int))
                    imps = pd.DataFrame({'Métrica': X_clf.columns, 
                                         'Importância (%)': rf.feature_importances_ * 100}).sort_values('Importância (%)', ascending=False)
                    
                    st.info("💡 **Análise de Esforço:** Qual variável tem mais impacto para fazer uma campanha ultrapassar a mediana de lucro?")
                    fig_bar = px.bar(imps, x='Métrica', y='Importância (%)', template='ggplot2', color='Importância (%)', color_continuous_scale='Blues')
                    st.plotly_chart(fig_bar, use_container_width=True)
                except: pass

            with tab3:
                try:
                    # GMM clusterizando as Campanhas, não mais os dias
                    X_scaled = StandardScaler().fit_transform(df[['investimento_ads', 'mcm']])
                    gmm = GaussianMixture(n_components=3, covariance_type='full', random_state=42)
                    df['Cluster_Num'] = gmm.fit_predict(X_scaled)
                    
                    medias = df.groupby('Cluster_Num')['mcm'].mean().sort_values()
                    mapa_nomes = {
                        medias.index[0]: '🔴 Campanhas de Risco (Ineficientes)',
                        medias.index[1]: '🟡 Campanhas Estáveis',
                        medias.index[2]: '🟢 Campanhas de Ouro (Alto Retorno)'
                    }
                    df['Momento'] = df['Cluster_Num'].map(mapa_nomes)
                    
                    st.info("💡 **Mapeamento:** Identificando grupos densos de campanhas pelo perfil de risco/retorno.")
                    fig_scatter = px.scatter(df, x='investimento_ads', y='mcm', color='Momento', template='ggplot2',
                                             labels={'investimento_ads': 'Gasto da Campanha (R$)', 'mcm': 'Retorno (R$)'})
                    st.plotly_chart(fig_scatter, use_container_width=True)
                except: pass

            with tab4:
                try:
                    X_xgb = df[['investimento_ads', 'alcance_organico']]
                    y_xgb = df['mcm']

                    modelo_xgb = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
                    modelo_xgb.fit(X_xgb, y_xgb)
                    
                    st.info("💡 **Simulador de ROAS:** O algoritmo XGBoost aprendeu os padrões históricos. Insira os dados de uma nova campanha para prever o lucro.")
                    
                    col_sim1, col_sim2, col_sim3 = st.columns(3)
                    sim_invest = col_sim1.number_input("Orçamento Previsto (R$)", min_value=10.0, value=150.0)
                    sim_alcance = col_sim2.number_input("Estimativa de Views (Alcance)", min_value=100, value=5000)
                    
                    X_futuro = pd.DataFrame({'investimento_ads': [sim_invest], 'alcance_organico': [sim_alcance]})
                    pred_mcm = modelo_xgb.predict(X_futuro)[0]
                    
                    col_sim3.metric("Lucro Direto Previsto (MCM)", f"R$ {pred_mcm:,.2f}")
                except Exception as e:
                    st.error("Dados insuficientes para simulação preditiva.")

            st.divider()
            st.subheader("🤖 Consultoria Executiva IA")
            
            if "relatorio_gerado" not in st.session_state:
                with st.spinner("Analisando as campanhas..."):
                    prompt_cfo = f"""
                    Você é um estrategista financeiro aconselhando uma marca que investe em anúncios no Facebook Ads.
                    O banco de dados apontou que já geraram uma Receita Atribuída de R${fat_total:,.2f} através de {qtd_campanhas} campanhas.
                    O modelo provou que cada visualização (alcance) adiciona em média R${peso_org:.4f} ao lucro da campanha.
                    
                    REGRAS:
                    1. Escreva 2 parágrafos animadores focados em negócios e criativos de anúncios.
                    2. É TOTALMENTE PROIBIDO usar os termos: 'econometria', 'VIF', 'Ridge', 'OLS', 'regressão', ou jargões estatísticos. 
                    3. Fale sobre como otimizar os criativos de anúncios baseados em alcance.
                    """
                    try:
                        st.session_state["relatorio_gerado"] = cfo_agent.run(prompt_cfo).content
                    except Exception as e:
                        st.session_state["relatorio_gerado"] = f"Erro na IA: {e}"
            
            st.write(st.session_state["relatorio_gerado"])
            
            if st.button("🎯 Gerar Táticas de Escala", type="primary", use_container_width=True):
                with st.spinner("Formatando as tarefas..."):
                    prompt_plano = f"Com base neste cenário financeiro: {st.session_state['relatorio_gerado']}. Escreva 3 passos práticos para o gestor de tráfego."
                    st.session_state["plano_acao_gerado"] = cfo_agent.run(prompt_plano).content
            
            if "plano_acao_gerado" in st.session_state:
                st.success("🔥 Plano de Tráfego Gerado!")
                st.markdown(st.session_state["plano_acao_gerado"])
        else:
            st.info("👋 Clique em 'Sincronizar Painel' para ver seus números.")
