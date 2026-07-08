import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
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
        st.title("📊 Painel Executivo: Finanças & Marketing")
        
        st.sidebar.header("⚙️ Parâmetros Financeiros")
        usar_dre = st.sidebar.toggle("Ativar Descontos Fixos", value=False, help="Ligue para ver o Lucro Líquido final após todos os custos da empresa.")
        
        if usar_dre:
            pct_cpv = st.sidebar.slider("Custo do Produto (%)", 0, 100, 30) / 100
            pct_gateway = st.sidebar.slider("Taxas de Cartão (%)", 0.0, 15.0, 5.0) / 100
            pct_imposto = st.sidebar.slider("Impostos (%)", 0.0, 30.0, 6.0) / 100
            custo_fixo_mensal = st.sidebar.number_input("Custo Fixo (R$)", min_value=0, value=3000)
            custo_fixo_diario = custo_fixo_mensal / 30
        else:
            pct_cpv = 0.0
            pct_gateway = 0.0
            pct_imposto = 0.0
            custo_fixo_diario = 0.0
        
        st.sidebar.divider()
        
        if st.sidebar.button("🛍️ Puxar Dados Externos (API)"):
            sucesso, msg = sincronizar_facebook_ads(st.session_state['usuario_email'])
            if sucesso: st.toast("Dados atualizados!")
            else: st.sidebar.error(msg)
        
        if st.sidebar.button("🚪 Sair"):
            st.session_state['autenticado'] = False
            st.session_state['dados_carregados'] = False
            st.rerun()

        # Agente CFO configurado para falar como um consultor de negócios
        groq_client = OpenAI(
            api_key=st.secrets.get("GROQ_API_KEY", ""),
            base_url="https://api.groq.com/openai/v1"
        )
        
        cfo_agent = Agent(
            model=OpenAIChat(id="llama-3.3-70b-versatile", client=groq_client),
            description="Você é um consultor financeiro focado em ajudar donos de e-commerce a aumentarem os lucros. Use linguagem simples, direta e de negócios."
        )

        if st.sidebar.button("☁️ Sincronizar Painel", type="primary"):
            with st.spinner("Processando histórico..."):
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
            
            csv_export = df.to_csv(index=False).encode('utf-8')
            st.sidebar.download_button(
                label="📥 Exportar Base (CSV)",
                data=csv_export,
                file_name="axiquant_base.csv",
                mime="text/csv"
            )
            
            df['custo_produtos'] = df['faturamento'] * pct_cpv
            df['taxas_gateway'] = df['faturamento'] * pct_gateway
            df['impostos'] = df['faturamento'] * pct_imposto
            df['custo_fixo_rateado'] = custo_fixo_diario
            df['lucro_liquido'] = df['faturamento'] - (df['investimento_ads'] + df['custo_produtos'] + df['taxas_gateway'] + df['impostos'] + df['custo_fixo_rateado'])
            df['mcm'] = df['faturamento'] - df['investimento_ads']
            
            fat_total = df['faturamento'].sum()
            inv_total = df['investimento_ads'].sum()
            mcm_total = df['mcm'].sum()
            lucro_total = df['lucro_liquido'].sum()
            
            margem_exibida = (mcm_total / fat_total) * 100 if not usar_dre else (lucro_total / fat_total) * 100
            label_lucro = "Receita de Marketing" if not usar_dre else "Lucro Líquido Real"
            valor_lucro = mcm_total if not usar_dre else lucro_total
            
            alcance_total = df['alcance_organico'].sum() if 'alcance_organico' in df.columns else 0
            engajamento_total = df['interacoes_engajamento'].sum() if 'interacoes_engajamento' in df.columns else 0
            
            st.markdown("### 🏢 Saúde do Negócio")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Faturamento", f"R$ {fat_total:,.2f}")
            kpi2.metric(label_lucro, f"R$ {valor_lucro:,.2f}", delta=f"{margem_exibida:.1f}% Margem")
            kpi3.metric("Alcance (Views)", f"{int(alcance_total):,}".replace(",", "."))
            kpi4.metric("Engajamento", f"{int(engajamento_total):,}".replace(",", "."))
            st.sidebar.metric("Total Investido (Ads)", f"R$ {inv_total:,.2f}")
            st.divider()

            st.header("🧠 Inteligência de Dados")
            # Nomes limpos e focados em negócios
            tab1, tab2, tab3, tab4 = st.tabs(["💸 Retorno por Canal", "🎯 Onde Focar", "🚥 Dias de Ouro", "🔮 Previsão de Vendas"])
            
            peso_organico = 0
            
            with tab1:
                st.subheader("Atribuição de Receita")
                st.write("A inteligência do AxiQuant analisou o histórico e calculou o retorno exato de cada esforço de marketing da empresa.")
                
                try:
                    features = ['investimento_ads', 'alcance_organico', 'posts_publicados']
                    X = df[features]
                    y = df['mcm']
                    
                    # Tenta OLS primeiro (Feijão com arroz)
                    X_ols = sm.add_constant(X)
                    modelo_ols = sm.OLS(y, X_ols).fit()
                    
                    peso_ads = modelo_ols.params.get('investimento_ads', 0)
                    peso_org = modelo_ols.params.get('alcance_organico', 0)
                    peso_posts = modelo_ols.params.get('posts_publicados', 0)
                    intercepto = modelo_ols.params.get('const', 0)
                    
                    # Lógica do AutoML: Se a multicolinearidade quebrou os pesos (ficou negativo), aplica Ridge silenciosamente
                    if peso_ads < 0 or peso_org < 0:
                        scaler_X = StandardScaler()
                        scaler_y = StandardScaler()
                        
                        X_scaled = scaler_X.fit_transform(X)
                        y_scaled = scaler_y.fit_transform(y.values.reshape(-1, 1)).flatten()
                        
                        ridge = Ridge(alpha=30.0) # Alpha travado nos bastidores
                        ridge.fit(X_scaled, y_scaled)
                        
                        std_X = scaler_X.scale_
                        std_y = scaler_y.scale_[0]
                        coef_originais = ridge.coef_ * (std_y / std_X)
                        intercepto = scaler_y.mean_[0] - np.sum(coef_originais * scaler_X.mean_)
                        
                        peso_ads = coef_originais[0]
                        peso_org = coef_originais[1]
                        peso_posts = coef_originais[2]
                        
                        # Guardamos na variável para o TCC saber que o fallback ativou
                        st.session_state['metodo_usado'] = "Ridge (Ajuste Automático)"
                    else:
                        st.session_state['metodo_usado'] = "Regressão OLS Padrão"

                    st.success(f"💡 **Conclusão da IA:** Cada visualização orgânica no seu perfil está gerando **R$ {peso_org:.4f}** para o seu negócio. Enquanto isso, cada R$ 1,00 colocado em Anúncios Pagos retorna **R$ {peso_ads:.2f}**.")
                    
                    df_coefs = pd.DataFrame({
                        "Canais de Aquisição": ["Base do Negócio (Inércia)", "Anúncios Pagos (R$)", "Tráfego Orgânico (Views)", "Postagens Diárias"],
                        "Impacto Direto (R$)": [intercepto, peso_ads, peso_org, peso_posts]
                    })
                    st.dataframe(df_coefs.style.format({"Impacto Direto (R$)": "{:,.2f}"}), use_container_width=True)
                except Exception as e: 
                    st.warning("Histórico insuficiente para calcular os retornos.")

            with tab2:
                try:
                    X_clf = df[['investimento_ads', 'alcance_organico', 'interacoes_engajamento', 'posts_publicados']]
                    rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['mcm'] > df['mcm'].median()).astype(int))
                    imps = pd.DataFrame({'Métrica': ['Anúncios', 'Alcance Orgânico', 'Engajamento', 'Qtd Posts'], 
                                         'Importância (%)': rf.feature_importances_ * 100}).sort_values('Importância (%)', ascending=False)
                    
                    st.info("💡 **Análise de Esforço:** Descubra o que tem mais peso na hora de bater as metas do mês.")
                    # Plotly: Gráfico estilo ggplot2
                    fig_bar = px.bar(imps, x='Métrica', y='Importância (%)', template='ggplot2', color='Importância (%)', color_continuous_scale='Blues')
                    st.plotly_chart(fig_bar, use_container_width=True)
                except: pass

            with tab3:
                try:
                    X_scaled = StandardScaler().fit_transform(df[['investimento_ads', 'mcm']])
                    gmm = GaussianMixture(n_components=3, covariance_type='full', random_state=42)
                    df['Cluster_Num'] = gmm.fit_predict(X_scaled)
                    
                    medias = df.groupby('Cluster_Num')['mcm'].mean().sort_values()
                    mapa_nomes = {
                        medias.index[0]: 'Dias de Risco (Atenção)',
                        medias.index[1]: 'Dias Estáveis',
                        medias.index[2]: 'Dias de Ouro (Alta Venda)'
                    }
                    df['Momento'] = df['Cluster_Num'].map(mapa_nomes)
                    
                    st.info("💡 **Mapeamento:** Veja como o seu faturamento reage de acordo com o valor que você investe.")
                    # Plotly: Gráfico de Dispersão limpo
                    fig_scatter = px.scatter(df, x='investimento_ads', y='mcm', color='Momento', template='ggplot2',
                                             labels={'investimento_ads': 'Gasto em Ads (R$)', 'mcm': 'Retorno (R$)'})
                    st.plotly_chart(fig_scatter, use_container_width=True)
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

                        df_futuro = pd.DataFrame({'Data': datas_futuras, 'Retorno Previsto (R$)': previsoes})
                        
                        st.info("💡 **Bússola de Vendas:** A Inteligência Artificial projetou o seu fluxo de caixa para a próxima semana.")
                        # Plotly: Gráfico de Linha preditivo
                        fig_line = px.line(df_futuro, x='Data', y='Retorno Previsto (R$)', template='ggplot2', markers=True)
                        st.plotly_chart(fig_line, use_container_width=True)
                    except Exception as e: pass
                else:
                    st.info(f"⏳ **Coletando dados ({dias_registrados}/14 dias)...**")

            st.divider()
            st.subheader("🤖 Consultoria Executiva IA")
            
            if "relatorio_gerado" not in st.session_state:
                with st.spinner("Analisando o fluxo de caixa..."):
                    # Prompt reformulado para bloquear jargões acadêmicos
                    prompt_cfo = f"""
                    Você é um Diretor Financeiro (CFO) experiente aconselhando o dono de uma loja.
                    O Faturamento atual é de R${fat_total:,.2f} e a Receita de Marketing é R${mcm_total:,.2f}.
                    A IA descobriu que cada visualização orgânica no Instagram/Tiktok gera R${peso_organico:.4f} de receita.
                    
                    REGRAS OBRIGATÓRIAS:
                    1. Escreva 2 parágrafos curtos, encorajadores e diretos.
                    2. Fale EXCLUSIVAMENTE sobre estratégia de negócios, vendas, conteúdo e como otimizar os lucros.
                    3. É TOTALMENTE PROIBIDO usar jargões acadêmicos. NÃO use as palavras: 'econometria', 'multicolinearidade', 'modelo Ridge', 'OLS', 'variáveis' ou 'coeficientes'. Fale a língua do lojista.
                    """
                    try:
                        st.session_state["relatorio_gerado"] = cfo_agent.run(prompt_cfo).content
                    except Exception as e:
                        st.session_state["relatorio_gerado"] = f"Erro na IA: {e}"
            
            st.write(st.session_state["relatorio_gerado"])
            
            if st.button("🎯 Gerar Plano de Ação Prático", type="primary", use_container_width=True):
                with st.spinner("Formatando as tarefas..."):
                    prompt_plano = f"Com base neste cenário financeiro: {st.session_state['relatorio_gerado']}. Escreva 3 passos práticos em formato de checklist que o dono da loja pode aplicar hoje mesmo no seu marketing para aumentar as vendas."
                    st.session_state["plano_acao_gerado"] = cfo_agent.run(prompt_plano).content
            
            if "plano_acao_gerado" in st.session_state:
                st.success("🔥 Plano de Marketing Gerado!")
                st.markdown(st.session_state["plano_acao_gerado"])
        else:
            st.info("👋 Clique em 'Sincronizar Painel' para ver seus números.")
