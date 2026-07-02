import streamlit as st
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from conexao_db import puxar_dados_nuvem, sincronizar_loja_shopify, sincronizar_facebook_ads
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from supabase import create_client
import os
import json
from openai import OpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

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

    # BARREIRA DE PAGAMENTO
    if not tem_acesso:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔒 Período de teste finalizado")
            st.markdown("### Plano AxiQuant Pro — R$ 57,00/mês")
            st.link_button("💳 Assinar via Stripe", STRIPE_LINK, type="primary", use_container_width=True)
            if st.button("Sair da Conta"):
                st.session_state['autenticado'] = False
                st.rerun()

    # ONBOARDING (CHAVES)
    elif not empresa.get('shopify_token') or not empresa.get('meta_token'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🚀 Bem-vindo ao AxiQuant!")
            with st.form("form_integracao"):
                shop_url = st.text_input("URL Shopify")
                shop_token = st.text_input("Token Shopify", type="password")
                meta_id = st.text_input("ID Meta Ads")
                meta_token = st.text_input("Token Meta", type="password")
                if st.form_submit_button("Salvar Chaves", type="primary", use_container_width=True):
                    supabase.table('empresas').update({"shopify_url": shop_url.replace("https://", ""), "shopify_token": shop_token, "meta_account_id": meta_id, "meta_token": meta_token}).eq('email_dono', st.session_state['usuario_email']).execute()
                    st.rerun()

    # PAINEL PRINCIPAL
    else:
        st.title("📊 Painel de Inteligência Executiva")
        
        if st.sidebar.button("🛍️ Sincronizar Shopify"):
            sucesso, msg = sincronizar_loja_shopify(st.session_state['usuario_email'])
            if sucesso: st.toast("Shopify Sincronizada!")
            else: st.sidebar.error(msg)
                    
        if st.sidebar.button("🔵 Sincronizar Facebook"):
            sucesso, msg = sincronizar_facebook_ads(st.session_state['usuario_email'])
            if sucesso: st.toast("Meta Sincronizado!")
            else: st.sidebar.error(msg)
        
        if st.sidebar.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.session_state['dados_carregados'] = False
            st.rerun()

        # =================================================================
        # 🧠 INTEGRAÇÃO PORTKEY AI (FALLBACK & LOAD BALANCING)
        # =================================================================
        chave_portkey = st.secrets.get("PORTKEY_API_KEY", "")
        
        # Configuração de Roteamento Inteligente
        portkey_config = {
            "strategy": {"mode": "fallback"},
            "targets": [
                {
                    "provider": "groq",
                    "api_key": st.secrets.get("GROQ_API_KEY", ""),
                    "override_params": {"model": "llama-3.3-70b-versatile"}
                },
                {
                    "provider": "openai", # O Paraquedas caso o Groq trave no limite
                    "api_key": st.secrets.get("OPENAI_API_KEY", "sk-chave-falsa-se-nao-tiver"),
                    "override_params": {"model": "gpt-4o-mini"}
                }
            ]
        }

        # Cria os headers oficiais da Portkey
        portkey_headers = createHeaders(
            api_key=chave_portkey,
            config=json.dumps(portkey_config)
        )

        # Injeta o Gateway da Portkey dentro do cliente padrão da OpenAI
        portkey_client = OpenAI(
            api_key="dummy_key", 
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=portkey_headers
        )

        # Conecta o Agente Agno ao cliente mascarado pela Portkey
        cfo_agent = Agent(
            model=OpenAIChat(id="llama-3.3-70b-versatile", client=portkey_client),
            description="Você é um CFO sênior de e-commerce e fundos quantitativos. Traduza métricas complexas para estratégias agressivas de lucro."
        )
        # =================================================================

        if st.sidebar.button("☁️ Sincronizar Operação", type="primary"):
            with st.spinner("Carregando base de dados..."):
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
            for col in ['leads', 'investimento_ads', 'ticket_medio', 'vendas_totais', 'churn', 'faturamento']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.sort_values('data').dropna()
            
            fat_total = df['faturamento'].sum()
            inv_total = df['investimento_ads'].sum()
            vendas = df['vendas_totais'].sum()
            roas = fat_total / inv_total if inv_total > 0 else 0
            
            st.markdown("### 📈 Raio-X Operacional")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Faturamento Total", f"R$ {fat_total:,.2f}")
            kpi2.metric("ROAS Geral", f"{roas:.2f}x")
            kpi3.metric("Vendas Totais", f"{int(vendas)}")
            kpi4.metric("Ticket Médio", f"R$ {df['ticket_medio'].mean():,.2f}")
            st.divider()

            st.header("🧠 Motores de Machine Learning")
            tab1, tab2, tab3, tab4 = st.tabs(["Causas (Regressão)", "Importância (Classificação)", "Padrões (Cluster)", "🔮 Previsão (Futuro)"])
            
            peso_ads = 0
            importancias_lista = ""
            
            with tab1:
                try:
                    X_reg = sm.add_constant(df[['investimento_ads', 'leads', 'ticket_medio']])
                    mod = sm.OLS(df['faturamento'], X_reg).fit()
                    peso_ads = mod.params.get('investimento_ads', 0)
                    st.info(f"💡 **O que isso significa na prática?**\nPara cada **R$ 1,00** investido em anúncios, sua operação retorna **R$ {peso_ads:.2f}**.")
                    st.dataframe(pd.DataFrame({"Métrica": mod.params.index, "Multiplicador": mod.params.values}).style.format({"Multiplicador": "{:.2f}"}))
                except: pass

            with tab2:
                try:
                    X_clf = df[['investimento_ads', 'leads', 'ticket_medio', 'churn']]
                    rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['faturamento'] > df['faturamento'].median()).astype(int))
                    imps = pd.DataFrame({'Métrica': X_clf.columns, 'Poder (%)': rf.feature_importances_ * 100}).sort_values('Poder (%)', ascending=False)
                    importancias_lista = imps.to_dict('records')
                    st.info("💡 **Onde focar sua energia?**\nFoque em otimizar a variável com a barra mais alta para alavancar receita.")
                    st.bar_chart(imps.set_index('Métrica'))
                except: pass

            with tab3:
                try:
                    df['Cluster'] = KMeans(n_clusters=3, random_state=42).fit_predict(StandardScaler().fit_transform(df[['investimento_ads', 'faturamento']])).astype(str)
                    st.info("💡 **Perfis de Dias:**\nPontos no topo à direita são seus *Dias de Ouro*. Repita o que fez neles!")
                    st.scatter_chart(df, x='investimento_ads', y='faturamento', color='Cluster')
                except: pass

            with tab4:
                dias_registrados = len(df)
                if dias_registrados >= 21:
                    try:
                        df_xgb = df.copy()
                        df_xgb['dia_semana'] = df_xgb['data'].dt.dayofweek
                        df_xgb['fat_ontem'] = df_xgb['faturamento'].shift(1)
                        df_xgb = df_xgb.dropna()

                        X_xgb = df_xgb[['investimento_ads', 'dia_semana', 'fat_ontem']]
                        y_xgb = df_xgb['faturamento']

                        modelo_xgb = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
                        modelo_xgb.fit(X_xgb, y_xgb)

                        datas_futuras = [df_xgb['data'].max() + pd.Timedelta(days=i) for i in range(1, 8)]
                        previsoes = []
                        fat_lag = df_xgb['faturamento'].iloc[-1]
                        for dt in datas_futuras:
                            X_futuro = pd.DataFrame({'investimento_ads': [df_xgb['investimento_ads'].tail(7).mean()], 'dia_semana': [dt.dayofweek], 'fat_ontem': [fat_lag]})
                            pred = modelo_xgb.predict(X_futuro)[0]
                            previsoes.append(pred)
                            fat_lag = pred

                        df_futuro = pd.DataFrame({'Data': datas_futuras, 'Faturamento Previsto': previsoes})
                        st.info("💡 **Previsão XGBoost:** Projeção desenhada com base em histórico avançado.")
                        st.line_chart(df_futuro.set_index('Data'))
                    except: pass
                else:
                    st.info(f"⏳ **Aprendizado XGBoost ({dias_registrados}/21 dias)**")

            st.divider()
            st.subheader("🤖 Parecer do CFO Artificial (Protegido por Portkey)")
            
            if "relatorio_gerado" not in st.session_state:
                with st.spinner("O CFO está analisando a estrutura de custos..."):
                    prompt_cfo = f"Dados macro: Faturamento total R${fat_total:.2f}, Ads R${inv_total:.2f}, ROAS {roas:.2f}x. Faça uma análise executiva em 2 parágrafos."
                    st.session_state["relatorio_gerado"] = cfo_agent.run(prompt_cfo).content
            
            st.write(st.session_state["relatorio_gerado"])
            
            if st.button("🎯 Transformar Parecer em Plano de Ação", type="primary"):
                with st.spinner("Desenhando e roteando requisição inteligente..."):
                    prompt_plano = f"Cenário: Fat R${fat_total:.2f}, Ads R${inv_total:.2f}, ROAS {roas:.2f}x. Parecer: {st.session_state['relatorio_gerado']}. Variáveis: {importancias_lista}. Crie um Plano Tático de 3 passos práticos para escalar lucro hoje."
                    st.session_state["plano_acao_gerado"] = cfo_agent.run(prompt_plano).content
            
            if "plano_acao_gerado" in st.session_state:
                st.success("🔥 Plano Estruturado!")
                st.markdown(st.session_state["plano_acao_gerado"])
        else:
            st.info("👋 Clique em 'Sincronizar Operação' na barra lateral.")
