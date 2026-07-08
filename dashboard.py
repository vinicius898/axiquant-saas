import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import xgboost as xgb
from conexao_db import puxar_dados_nuvem, sincronizar_loja_shopify, sincronizar_facebook_ads
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from supabase import create_client
from openai import OpenAI

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

# 2. Inicialização de Estado
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
        st.markdown("O cérebro financeiro do seu negócio.")
        
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
    dias_restantes = 0
    
    if empresa.get('data_expiracao_trial'):
        expiracao = pd.to_datetime(empresa['data_expiracao_trial'], utc=True)
        dias_restantes = (expiracao - agora).days
        if dias_restantes >= 0:
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
        st.title("📊 Painel Executivo: Finanças & Mídias Sociais")
        
        st.sidebar.header("⚙️ Parâmetros Financeiros (DRE)")
        
        # Botão Liga/Desliga para o DRE estrutural
        usar_dre = st.sidebar.toggle("📊 Ativar Descontos do DRE", value=False, help="Desligue para a IA avaliar puramente a Margem de Contribuição do Marketing.")
        
        if usar_dre:
            pct_cpv = st.sidebar.slider("Custo de Produto/Serviço (CPV %)", 0, 100, 30) / 100
            pct_gateway = st.sidebar.slider("Taxa de Cartão/Gateway (%)", 0.0, 15.0, 5.0) / 100
            pct_imposto = st.sidebar.slider("Impostos Médios (%)", 0.0, 30.0, 6.0) / 100
            custo_fixo_mensal = st.sidebar.number_input("Custo Fixo Mensal (R$)", min_value=0, value=3000)
            custo_fixo_diario = custo_fixo_mensal / 30
        else:
            pct_cpv = 0.0
            pct_gateway = 0.0
            pct_imposto = 0.0
            custo_fixo_diario = 0.0
        
        st.sidebar.divider()
        
        if st.sidebar.button("🛍️ Sincronizar Operação Externa"):
            sucesso, msg = sincronizar_facebook_ads(st.session_state['usuario_email'])
            if sucesso: st.toast("Sincronização Concluída!")
            else: st.sidebar.error(msg)
        
        if st.sidebar.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.session_state['dados_carregados'] = False
            st.rerun()

        # --- CONEXÃO DIRETA GROQ (SEM PORTKEY) ---
        groq_client = OpenAI(
            api_key=st.secrets.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1"
        )
        
        cfo_agent = Agent(
            model=OpenAIChat(id="llama-3.3-70b-versatile", client=groq_client),
            description="Você é um CFO sênior quantitativo e econometrista. Traduza métricas de redes sociais, modelos de regressão Ridge e Margens de Contribuição de Marketing (MCM) para estratégias de maximização de caixa corporativo."
        )

        if st.sidebar.button("☁️ Sincronizar Painel Interno", type="primary"):
            with st.spinner("Carregando base de dados financeira e de marketing..."):
                dados = puxar_dados_nuvem(st.session_state['usuario_email'])
                if dados:
                    st.session_state['dados_loja'] = dados
                    st.session_state['dados_carregados'] = True
                    if "relatorio_gerado" in st.session_state: del st.session_state["relatorio_gerado"]
                    if "plano_acao_gerado" in st.session_state: del st.session_state["plano_acao_gerado"]
                    st.rerun()

        if st.session_state['dados_carregados'] and st.session_state['dados_loja']:
            df = pd.DataFrame(st.session_state['dados_loja'])
            df['data'] = pd.to_datetime(df['data'])
            
            colunas_numericas = ['leads', 'investimento_ads', 'ticket_medio', 'faturamento', 
                                 'alcance_organico', 'interacoes_engajamento', 'posts_publicados']
            for col in colunas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            df = df.sort_values('data').dropna()
            
            # --- INTEGRAÇÃO DO BOTÃO DE DOWNLOAD DO CSV ---
            csv_export = df.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="📥 Baixar Dados (CSV)",
                data=csv_export,
                file_name="axiquant_base_historica.csv",
                mime="text/csv",
                help="Exporte a base completa de 4 anos da Meta Robyn para rodar análises em R ou Python."
            )
            
            # Cálculo de Lucro Operacional Líquido
            df['custo_produtos'] = df['faturamento'] * pct_cpv
            df['taxas_gateway'] = df['faturamento'] * pct_gateway
            df['impostos'] = df['faturamento'] * pct_imposto
            df['custo_fixo_rateado'] = custo_fixo_diario
            df['lucro_liquido'] = df['faturamento'] - (df['investimento_ads'] + df['custo_produtos'] + df['taxas_gateway'] + df['impostos'] + df['custo_fixo_rateado'])
            
            # NOVO ALVO METODOLÓGICO: Margem de Contribuição do Marketing (MCM)
            df['mcm'] = df['faturamento'] - df['investimento_ads']
            
            fat_total = df['faturamento'].sum()
            inv_total = df['investimento_ads'].sum()
            mcm_total = df['mcm'].sum()
            lucro_total = df['lucro_liquido'].sum()
            
            # Margem calculada sobre a realidade ativa escolhida no painel
            margem_exibida = (mcm_total / fat_total) * 100 if not usar_dre else (lucro_total / fat_total) * 100
            label_lucro = "Margem de Marketing (MCM)" if not usar_dre else "Lucro Líquido Real"
            valor_lucro = mcm_total if not usar_dre else lucro_total
            
            alcance_total = df['alcance_organico'].sum() if 'alcance_organico' in df.columns else 0
            engajamento_total = df['interacoes_engajamento'].sum() if 'interacoes_engajamento' in df.columns else 0
            
            st.markdown("### 🏢 Saúde Corporativa (Global)")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Faturamento Bruto", f"R$ {fat_total:,.2f}")
            kpi2.metric(label_lucro, f"R$ {valor_lucro:,.2f}", delta=f"{margem_exibida:.1f}% Margem")
            kpi3.metric("Alcance Orgânico (Views)", f"{int(alcance_total):,}".replace(",", "."))
            kpi4.metric("Interações (Engajamento)", f"{int(engajamento_total):,}".replace(",", "."))
            st.sidebar.metric("💰 Total Investido em Ads", f"R$ {inv_total:,.2f}")
            st.divider()

            st.header("🧠 Inteligência Artificial Aplicada")
            tab1, tab2, tab3, tab4 = st.tabs(["ROI Social Media (Ridge Regression)", "Pesos Operacionais (RF)", "Perfis de Risco (GMM)", "🔮 Previsão de Caixa"])
            
            with tab1:
                st.subheader("🛡️ Resolução de Multicolinearidade via Regularização L2 (Ridge)")
                st.write("Em Marketing Mix Modeling (MMM), variáveis de tráfego pago e alcance orgânico possuem alta correlação, quebrando regressões comuns (OLS). Ajuste o fator **Alpha** para penalizar a variância e estabilizar os ROIs reais positivos.")
                
                # Slider dinâmico para o Alpha da Regressão Ridge
                ridge_alpha = st.slider("Fator de Penalização Estatística (Alpha L2)", min_value=0.1, max_value=200.0, value=30.0, step=1.0)
                
                try:
                    features = ['investimento_ads', 'alcance_organico', 'posts_publicados']
                    X = df[features]
                    y = df['mcm']
                    
                    # 1. Padronização estrita (Obrigatória para Ridge)
                    scaler_X = StandardScaler()
                    scaler_y = StandardScaler()
                    
                    X_scaled = scaler_X.fit_transform(X)
                    y_scaled = scaler_y.fit_transform(y.values.reshape(-1, 1)).flatten()
                    
                    # 2. Treinamento do Modelo Ridge
                    modelo_ridge = Ridge(alpha=ridge_alpha)
                    modelo_ridge.fit(X_scaled, y_scaled)
                    
                    # 3. Engenharia Reversa Estatística: Despadronizar coeficientes para manter interpretação em Reais (R$)
                    std_X = scaler_X.scale_
                    std_y = scaler_y.scale_[0]
                    coef_originais = modelo_ridge.coef_ * (std_y / std_X)
                    intercepto_original = scaler_y.mean_[0] - np.sum(coef_originais * scaler_X.mean_)
                    
                    peso_ads = coef_originais[0]
                    peso_organico = coef_originais[1]
                    peso_posts = coef_originais[2]
                    
                    st.success(f"💡 **Prova de Atribuição Corrigida (L2):** O modelo calculou que cada **1 visualização orgânica** agregou **R$ {peso_organico:.4f}** à Margem de Marketing, enquanto cada R$ 1,00 investido em anúncios retornou **R$ {peso_ads:.2f}** em receita incremental.")
                    
                    df_coefs = pd.DataFrame({
                        "Métrica Operacional": ["Intercepto (Base Estável)", "Investimento Meta/Search Ads (R$)", "Alcance Orgânico (Views)", "Frequência de Posts Diários"],
                        "Impacto Direto na Margem (R$)": [intercepto_original, peso_ads, peso_organico, peso_posts]
                    })
                    st.dataframe(df_coefs.style.format({"Impacto Direto na Margem (R$)": "{:,.4f}"}))
                except Exception as e: 
                    st.warning(f"Erro ao processar matriz Ridge: {e}")

            with tab2:
                try:
                    X_clf = df[['investimento_ads', 'alcance_organico', 'interacoes_engajamento', 'posts_publicados']]
                    rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['mcm'] > df['mcm'].median()).astype(int))
                    imps = pd.DataFrame({'Métrica': X_clf.columns, 'Poder de Decisão (%)': rf.feature_importances_ * 100}).sort_values('Poder de Decisão (%)', ascending=False)
                    st.info("💡 **Onde focar sua energia?** O algoritmo avalia de forma não-linear qual canal possui maior relevância para romper a mediana histórica de receita.")
                    st.bar_chart(imps.set_index('Métrica'))
                except: pass

            with tab3:
                try:
                    # GMM focado na dispersão de investimentos vs retorno real de marketing
                    X_scaled = StandardScaler().fit_transform(df[['investimento_ads', 'mcm']])
                    gmm = GaussianMixture(n_components=3, covariance_type='full', random_state=42)
                    df['Cluster_Num'] = gmm.fit_predict(X_scaled)
                    
                    medias = df.groupby('Cluster_Num')['mcm'].mean().sort_values()
                    mapa_nomes = {
                        medias.index[0]: '🔴 Eficiência Baixa / Risco',
                        medias.index[1]: '🟡 Eficiência Média / Estável',
                        medias.index[2]: '🟢 Dias de Ouro / Alta Tração'
                    }
                    df['Perfil de Risco'] = df['Cluster_Num'].map(mapa_nomes)
                    
                    st.info("💡 **Mapeamento Probabilístico (GMM):** Agrupamento elíptico por densidade que isola os dias de maior e menor retorno sobre o investimento de mídia.")
                    st.scatter_chart(df, x='investimento_ads', y='mcm', color='Perfil de Risco')
                except: pass

            with tab4:
                dias_registrados = len(df)
                if dias_registrados >= 14: 
                    try:
                        df_xgb = df.copy()
                        df_xgb['dia_semana'] = df_xgb['data'].dt.dayofweek
                        df_xgb['mcm_ontem'] = df_xgb['mcm'].shift(1)
                        df_xgb = df_xgb.dropna()

                        X_xgb = df_xgb[['investimento_ads', 'alcance_organico', 'dia_semana', 'mcm_ontem']]
                        y_xgb = df_xgb['mcm']

                        modelo_xgb = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
                        modelo_xgb.fit(X_xgb, y_xgb)

                        datas_futuras = [df_xgb['data'].max() + pd.Timedelta(days=i) for i in range(1, 8)]
                        previsoes = []
                        mcm_lag = df_xgb['mcm'].iloc[-1]
                        media_ads = df_xgb['investimento_ads'].tail(7).mean()
                        media_org = df_xgb['alcance_organico'].tail(7).mean()
                        
                        for dt in datas_futuras:
                            X_futuro = pd.DataFrame({'investimento_ads': [media_ads], 'alcance_organico': [media_org], 'dia_semana': [dt.dayofweek], 'mcm_ontem': [mcm_lag]})
                            pred = modelo_xgb.predict(X_futuro)[0]
                            previsoes.append(pred)
                            mcm_lag = pred

                        df_futuro = pd.DataFrame({'Data': datas_futuras, 'Margem Prevista (R$)': previsoes})
                        df_futuro['Data'] = df_futuro['Data'].dt.strftime('%Y-%m-%d')
                        
                        st.info("💡 **Previsão Avançada XGBoost:** Projeção estocástica do comportamento de caixa para a próxima semana baseada na tendência histórica da Meta.")
                        st.line_chart(df_futuro.set_index('Data'))
                    except Exception as e:
                        st.error(f"Erro no XGBoost: {e}")
                else:
                    st.info(f"⏳ **Aprendizado Preditivo ({dias_registrados}/14 dias históricos)**")

            st.divider()
            st.subheader("🤖 Diagnóstico Executivo do CFO Artificial")
            
            if "relatorio_gerado" not in st.session_state:
                with st.spinner("Analisando matriz Ridge de Mídias Sociais..."):
                    prompt_cfo = f"Dados: Fat Bruto R${fat_total:.2f}, MCM Total R${mcm_total:.2f}, Alcance {alcance_total}. O modelo Ridge corrigiu a multicolinearidade e isolou que o alcance orgânico gera R${peso_organico:.4f} por view. Forneça uma análise de econometria robusta em 2 parágrafos provando o valor do conteúdo e explicando por que a regularização Ridge foi necessária para corrigir distorções de dados."
                    try:
                        st.session_state["relatorio_gerado"] = cfo_agent.run(prompt_cfo).content
                    except Exception as e:
                        st.session_state["relatorio_gerado"] = f"Erro na comunicação com a API Groq: {e}"
            
            st.write(st.session_state["relatorio_gerado"])
            
            if st.button("🎯 Transformar Parecer em Plano de Ação", type="primary", use_container_width=True):
                with st.spinner("Formatando tarefas táticas e editoriais..."):
                    prompt_plano = f"Cenário de Atribuição: Alcance {alcance_total}, Peso Orgânico {peso_organico:.4f}. Parecer: {st.session_state['relatorio_gerado']}. Monte 3 passos táticos para otimizar as postagens orgânicas baseando-se no ganho incremental calculado pelo modelo Ridge."
                    st.session_state["plano_acao_gerado"] = cfo_agent.run(prompt_plano).content
            
            if "plano_acao_gerado" in st.session_state:
                st.success("🔥 Plano de Mídias Sociais Orientado a Lucro Prontificado!")
                st.markdown(st.session_state["plano_acao_gerado"])
        else:
            st.info("👋 Clique em 'Sincronizar Painel Interno' para carregar as métricas híbridas.")
