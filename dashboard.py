import streamlit as st
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from conexao_db import puxar_dados_nuvem, sincronizar_loja_shopify, sincronizar_facebook_ads
from agno.agent import Agent
from agno.models.groq import Groq
from supabase import create_client
import os

# 1. Configuração da Página e CSS Customizado
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

# 2. Inicialização de Estado (Memória do Aplicativo)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
    st.session_state['usuario_email'] = ""
if 'dados_carregados' not in st.session_state:
    st.session_state['dados_carregados'] = False
if 'dados_loja' not in st.session_state:
    st.session_state['dados_loja'] = None

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
STRIPE_LINK = "https://buy.stripe.com/test_dRm4gy9uy5xC7y7bPDdAk00"

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
            if st.button("Criar Conta Grátis (7 Dias de Teste)", type="primary", use_container_width=True):
                with st.spinner("Preparando seu cofre de dados..."):
                    try:
                        resposta = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                        st.success("Conta criada com sucesso! Vá na aba 'Já tenho conta' e faça seu primeiro login.")
                    except Exception as e:
                        st.error(f"O Supabase relatou o seguinte erro: {e}")

# 4. ÁREA LOGADA (PAYWALL, ONBOARDING OU DASHBOARD)
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
        st.toast("Pagamento Identificado! Obrigado por assinar.", icon="🎉")

    # Controle de Acesso / Período de Teste
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

    # --- 4.1 BARREIRA DE PAGAMENTO ---
    if not tem_acesso:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔒 Seu período de teste terminou")
            st.warning("O seu CFO Artificial está pausado. Assine o plano Pro para reativar suas análises.")
            st.markdown("### Plano AxiQuant Pro — R$ 57,00/mês")
            st.divider()
            st.link_button("💳 Assinar via Cartão de Crédito (Stripe)", STRIPE_LINK, type="primary", use_container_width=True)
            if st.button("🚪 Sair da Conta", use_container_width=True):
                st.session_state['autenticado'] = False
                st.session_state['usuario_email'] = ""
                st.rerun()

    # --- 4.2 TELA DE ONBOARDING (CONFIGURAÇÃO DE CHAVES) ---
    elif not empresa.get('shopify_token') or not empresa.get('meta_token'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🚀 Bem-vindo ao AxiQuant!")
            if not assinatura_ativa and trial_valido:
                st.info(f"⏳ Você tem **{dias_restantes} dias de teste gratuito**. Conecte sua operação abaixo.")
            else:
                st.info("Para ativarmos o seu CFO Artificial, precisamos conectar a sua operação.")
            
            with st.form("form_integracao"):
                shop_url = st.text_input("URL da Loja Shopify")
                shop_token = st.text_input("Token da API do Admin Shopify", type="password")
                meta_id = st.text_input("ID da Conta de Anúncios Meta")
                meta_token = st.text_input("Token de Acesso Meta (Graph API)", type="password")
                
                if st.form_submit_button("Salvar Chaves e Ativar Painel", type="primary", use_container_width=True):
                    if shop_url and shop_token and meta_id and meta_token:
                        supabase.table('empresas').update({
                            "shopify_url": shop_url.replace("https://", ""),
                            "shopify_token": shop_token,
                            "meta_account_id": meta_id,
                            "meta_token": meta_token
                        }).eq('email_dono', st.session_state['usuario_email']).execute()
                        st.success("Redirecionando para o painel...")
                        st.rerun()
                    else:
                        st.warning("Preencha todos os campos.")
        if st.sidebar.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.rerun()
            
    # --- 4.3 O PAINEL EXECUTIVO PRINCIPAL ---
    else:
        st.title("📊 Painel de Inteligência Executiva")
        
        if not assinatura_ativa and trial_valido:
            st.sidebar.warning(f"⏳ **Teste Gratuito:** {dias_restantes} dias restantes.\n\n[Fazer Upgrade para Pro]({STRIPE_LINK})")
            st.sidebar.divider()
        
        if st.sidebar.button("🛍️ Sincronizar Shopify"):
            with st.spinner("Varrendo API da Shopify..."):
                sucesso, mensagem = sincronizar_loja_shopify(st.session_state['usuario_email'])
                if sucesso: st.toast("Shopify Sincronizada!", icon="🛍️")
                else: st.sidebar.error(mensagem)
                    
        if st.sidebar.button("🔵 Sincronizar Facebook Ads"):
            with st.spinner("Varrendo Meta Ads..."):
                sucesso, mensagem = sincronizar_facebook_ads(st.session_state['usuario_email'])
                if sucesso: st.toast("Meta Ads Sincronizado!", icon="🔵")
                else: st.sidebar.error(mensagem)
        
        if st.sidebar.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.session_state['dados_carregados'] = False
            st.rerun()

        # Configura o Agente de IA
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
        cfo_agent = Agent(
            model=Groq(id="llama-3.3-70b-versatile"), 
            description="Você é um CFO sênior de e-commerce e fundos quantitativos. Traduza métricas complexas para estratégias agressivas de lucro."
        )

        # Botão disparador que salva o estado dos dados na memória
        if st.sidebar.button("☁️ Sincronizar Operação", type="primary"):
            with st.spinner("Carregando base de dados..."):
                dados = puxar_dados_nuvem(st.session_state['usuario_email'])
                if dados:
                    st.session_state['dados_loja'] = dados
                    st.session_state['dados_carregados'] = True
                    # Limpa memórias antigas de relatórios para forçar uma nova análise limpa
                    if "relatorio_gerado" in st.session_state: del st.session_state["relatorio_gerado"]
                    if "plano_acao_gerado" in st.session_state: del st.session_state["plano_acao_gerado"]
                    st.rerun()

        # Renderização da Interface condicionado à memória ativa dos dados
        if st.session_state['dados_carregados'] and st.session_state['dados_loja']:
            df = pd.DataFrame(st.session_state['dados_loja'])
            df['data'] = pd.to_datetime(df['data'])
            for col in ['leads', 'investimento_ads', 'ticket_medio', 'vendas_totais', 'churn', 'faturamento']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.sort_values('data').dropna()
            
            # Cálculo de KPIs Globais
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
            
            # --- ABA 1: REGRESSÃO ---
            with tab1:
                try:
                    X_reg = sm.add_constant(df[['investimento_ads', 'leads', 'ticket_medio']])
                    mod = sm.OLS(df['faturamento'], X_reg).fit()
                    peso_ads = mod.params.get('investimento_ads', 0)
                    
                    st.info(f"💡 **O que isso significa na prática para o seu bolso?**\nO algoritmo de regressão cruzou seus dados históricos e descobriu que, para cada **R$ 1,00** investido em anúncios, sua operação gera de forma direta **R$ {peso_ads:.2f}** de faturamento. Monitore esse multiplicador: se ele cair abaixo de 1.00, você está queimando caixa ao tentar escalar campanhas.")
                    st.dataframe(pd.DataFrame({"Variável Operacional": mod.params.index, "Multiplicador de Receita (Peso)": mod.params.values}).style.format({"Multiplicador de Receita (Peso)": "{:.2f}"}))
                except: pass

            # --- ABA 2: CLASSIFICAÇÃO ---
            with tab2:
                try:
                    X_clf = df[['investimento_ads', 'leads', 'ticket_medio', 'churn']]
                    rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['faturamento'] > df['faturamento'].median()).astype(int))
                    imps = pd.DataFrame({'Métrica': X_clf.columns, 'Poder de Impacto (%)': rf.feature_importances_ * 100}).sort_values('Poder de Impacto (%)', ascending=False)
                    importancias_lista = imps.to_dict('records')
                    
                    st.info("💡 **Onde você deve focar sua energia para crescer?**\nEste gráfico de árvore de decisão calcula qual dessas métricas tem o maior poder matemático de fazer o faturamento da sua loja explodir ou despencar. Não tente arrumar tudo ao mesmo tempo: concentre seus esforços e seu orçamento na barra mais alta da tabela.")
                    st.bar_chart(imps.set_index('Métrica'))
                except: pass

            # --- ABA 3: CLUSTERIZAÇÃO ---
            with tab3:
                try:
                    df['Cluster'] = KMeans(n_clusters=3, random_state=42).fit_predict(StandardScaler().fit_transform(df[['investimento_ads', 'faturamento']])).astype(str)
                    
                    st.info("💡 **Mapeamento de Comportamento dos Seus Dias de Operação:**\nA inteligência artificial agrupou os dias da sua empresa em 3 perfis diferentes:\n* **Dias no topo à direita:** São os seus *Dias de Ouro* (Alto investimento trazendo retorno altíssimo). Abra o histórico e veja quais produtos e criativos rodaram nessas datas!\n* **Dias embaixo à esquerda:** São os seus *Dias de Alerta* (Baixo volume ou dinheiro desperdiçado).")
                    st.scatter_chart(df, x='investimento_ads', y='faturamento', color='Cluster')
                except: pass

            # --- ABA 4: PREVISÃO (XGBOOST) ---
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
                        media_ads = df_xgb['investimento_ads'].tail(7).mean()
                        fat_lag = df_xgb['faturamento'].iloc[-1]

                        previsoes = []
                        for dt in datas_futuras:
                            X_futuro = pd.DataFrame({'investimento_ads': [media_ads], 'dia_semana': [dt.dayofweek], 'fat_ontem': [fat_lag]})
                            pred = modelo_xgb.predict(X_futuro)[0]
                            previsoes.append(pred)
                            fat_lag = pred

                        df_futuro = pd.DataFrame({'Data': datas_futuras, 'Faturamento Previsto (R$)': previsoes})
                        
                        st.info("💡 **A Tendência de Caixa dos Próximos 7 Dias:**\nO algoritmo preditivo **XGBoost** avaliou os ciclos de venda anteriores e desenhou o comportamento esperado do faturamento para a próxima semana, assumindo a manutenção das métricas atuais.")
                        st.line_chart(df_futuro.set_index('Data'))
                        st.success(f"📈 Modelo calibrado! A previsão cumulativa de faturamento para os próximos 7 dias é de **R$ {sum(previsoes):,.2f}**.")
                    except Exception as e:
                        st.error(f"Erro na modelagem preditiva: {e}")
                else:
                    st.info(f"⏳ **Fase de Aprendizado do Algoritmo Avançado ({dias_registrados}/21 dias)**")
                    st.write("O motor preditivo com **XGBoost** precisa de um histórico mínimo de 21 dias para mapear corretamente a sazonalidade do seu negócio. Continue gerando dados e vendendo para habilitar essa ferramenta!")
                    st.progress(min(dias_registrados / 21, 1.0))

            st.divider()
            st.subheader("🤖 Parecer do CFO Artificial")
            
            # Gera o parecer financeiro inicial e guarda na memória
            if "relatorio_gerado" not in st.session_state:
                with st.spinner("O CFO está lendo as matrizes de dados..."):
                    prompt_cfo = f"Dados macro: Faturamento total R${fat_total:.2f}, Investimento Ads R${inv_total:.2f}, ROAS {roas:.2f}x. Faça uma análise de alto nível executivo em dois parágrafos curtos sobre a saúde do negócio."
                    st.session_state["relatorio_gerado"] = cfo_agent.run(prompt_cfo).content
            
            st.write(st.session_state["relatorio_gerado"])
            st.write("")
            
            # --- O BOTÃO DE OURO: PLANO DE AÇÃO ---
            if st.button("🎯 Transformar Parecer em Plano de Ação", type="primary", use_container_width=True):
                with st.spinner("Desenhando e priorizando tarefas prioritárias..."):
                    prompt_plano = f"Cenário financeiro: Faturamento R${fat_total:.2f}, Investimento Ads R${inv_total:.2f}, ROAS {roas:.2f}x. O parecer anterior foi: {st.session_state['relatorio_gerado']}. Com base na importância de variáveis calculada ({importancias_lista}) e o multiplicador de anúncios ({peso_ads:.2f}), trace um Plano de Ação Tático e Pragmático de exatamente 3 passos imediatos (Passo 1, Passo 2, Passo 3) focado em alavancar a margem de lucro líquida hoje. Dê exemplos palpáveis de mudanças em criativos, público ou ofertas."
                    st.session_state["plano_acao_gerado"] = cfo_agent.run(prompt_plano).content
            
            # Se o plano de ação foi gerado, renderiza logo abaixo na tela
            if "plano_acao_gerado" in st.session_state:
                st.success("🔥 Plano de Ação Tático Estruturado!")
                st.markdown(st.session_state["plano_acao_gerado"])

        else:
            st.info("👋 Painel pronto para análise. Clique no botão verde **'Sincronizar Operação'** localizado na barra lateral esquerda para acionar os motores de Inteligência Artificial.")
