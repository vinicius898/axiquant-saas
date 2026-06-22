import streamlit as st
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
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

# 2. Inicialização de Estado (Memória do Login e da IA)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
    st.session_state['usuario_email'] = ""

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
            senha_cad = st.text_input("Crie uma Senha (mínimo 6 caracteres)", type="password", key="cad_senha")
            if st.button("Criar Conta Grátis (7 Dias de Teste)", type="primary", use_container_width=True):
                with st.spinner("Preparando seu cofre de dados..."):
                    try:
                        resposta = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                        st.success("Conta criada com sucesso! Vá na aba 'Já tenho conta' e faça seu primeiro login.")
                    except Exception as e:
                        st.error(f"O Supabase relatou o seguinte erro: {e}")

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
        st.toast("Pagamento Identificado! Obrigado por assinar.", icon="🎉")

    # Controle de Trial
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

    # PAYWALL
    if not tem_acesso:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔒 Seu período de teste terminou")
            st.warning("O seu CFO Artificial está pausado. Assine o plano Pro para reativar suas sincronizações e análises preditivas.")
            st.markdown("### Plano AxiQuant Pro — R$ 57,00/mês")
            st.divider()
            st.link_button("💳 Assinar via Cartão de Crédito (Stripe)", STRIPE_LINK, type="primary", use_container_width=True)
            if st.button("🚪 Sair da Conta", use_container_width=True):
                st.session_state['autenticado'] = False
                st.session_state['usuario_email'] = ""
                st.rerun()

    # ONBOARDING (Chaves)
    elif not empresa.get('shopify_token') or not empresa.get('meta_token'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🚀 Bem-vindo ao AxiQuant!")
            if not assinatura_ativa and trial_valido:
                st.info(f"⏳ Você tem **{dias_restantes} dias de teste gratuito**. Conecte sua operação abaixo para começar.")
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
            
    # PAINEL PRINCIPAL
    else:
        st.title("📊 Painel de Inteligência Executiva")
        
        if not assinatura_ativa and trial_valido:
            st.sidebar.warning(f"⏳ **Teste Gratuito:** {dias_restantes} dias restantes.\n\n[Fazer Upgrade para Pro]({STRIPE_LINK})")
            st.sidebar.divider()
        
        if st.sidebar.button("🛍️ Sincronizar Shopify"):
            with st.spinner("Varrendo API da Shopify..."):
                sucesso, mensagem = sincronizar_loja_shopify(st.session_state['usuario_email'])
                if sucesso: st.toast("Shopify OK!", icon="🛍️")
                else: st.sidebar.error(mensagem)
                    
        if st.sidebar.button("🔵 Sincronizar Facebook Ads"):
            with st.spinner("Varrendo Meta Ads..."):
                sucesso, mensagem = sincronizar_facebook_ads(st.session_state['usuario_email'])
                if sucesso: st.toast("Meta OK!", icon="🔵")
                else: st.sidebar.error(mensagem)
        
        if st.sidebar.button("🚪 Sair do Sistema"):
            st.session_state['autenticado'] = False
            st.rerun()

        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
        cfo_agent = Agent(model=Groq(id="llama-3.3-70b-versatile"), description="Você é um CFO sênior de um fundo quantitativo. Seja analítico, estratégico e use português claro de negócios.")

        if st.sidebar.button("☁️ Sincronizar Operação", type="primary"):
            with st.spinner("Processando dados exclusivos..."):
                dados = puxar_dados_nuvem(st.session_state['usuario_email']) 
                if dados and len(dados) > 0:
                    df = pd.DataFrame(dados)
                    df['data'] = pd.to_datetime(df['data'])
                    for col in ['leads', 'investimento_ads', 'ticket_medio', 'vendas_totais', 'churn', 'faturamento']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    df = df.sort_values('data').dropna()
                    
                    # KPIs
                    fat_total = df['faturamento'].sum()
                    inv_total = df['investimento_ads'].sum()
                    vendas = df['vendas_totais'].sum()
                    roas = fat_total / inv_total if inv_total > 0 else 0
                    
                    st.markdown("### 📈 Raio-X Operacional")
                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                    kpi1.metric("Faturamento Total", f"R$ {fat_total:,.2f}")
                    kpi2.metric("ROAS (Retorno)", f"{roas:.2f}x")
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
                            
                            # TRADUÇÃO EXECUTIVA DA REGRESSÃO
                            st.info(f"💡 **O que isso significa na prática?**\nA matemática aponta que, em média, para cada **R$ 1,00** que você coloca em anúncios, o seu sistema retorna **R$ {peso_ads:.2f}** em faturamento. Se esse número estiver abaixo de 1, você está operando no prejuízo ao tentar escalar.")
                            
                            st.dataframe(pd.DataFrame({"Métrica": mod.params.index, "Multiplicador de Receita": mod.params.values}).style.format({"Multiplicador de Receita": "{:.2f}"}))
                        except: pass

                    with tab2:
                        try:
                            X_clf = df[['investimento_ads', 'leads', 'ticket_medio', 'churn']]
                            rf = RandomForestClassifier(random_state=42, n_estimators=50).fit(X_clf, (df['faturamento'] > df['faturamento'].median()).astype(int))
                            imps = pd.DataFrame({'Variável': X_clf.columns, 'Poder (%)': rf.feature_importances_ * 100}).sort_values('Poder (%)', ascending=False)
                            importancias_lista = imps.to_dict('records')
                            
                            # TRADUÇÃO EXECUTIVA DA CLASSIFICAÇÃO
                            st.info("💡 **Onde você deve focar sua energia?**\nEste gráfico mostra qual métrica tem o MAIOR impacto para fazer o faturamento da sua loja subir. Foque seus esforços em otimizar a variável com a barra mais alta.")
                            
                            st.bar_chart(imps.set_index('Variável'))
                        except: pass

                    with tab3:
                        try:
                            df['Cluster'] = KMeans(n_clusters=3, random_state=42).fit_predict(StandardScaler().fit_transform(df[['investimento_ads', 'faturamento']])).astype(str)
                            
                            # TRADUÇÃO EXECUTIVA DA CLUSTERIZAÇÃO
                            st.info("💡 **Os 3 Perfis de Dias da sua Loja:**\nA Inteligência Artificial agrupou seus dias de operação em 3 cores (Perfis).\n* Olhe para a cor que está mais no **topo à direita**: Esses são os seus *Dias de Ouro* (Alto Investimento e Alto Faturamento). Mapeie o que vendeu nesses dias!\n* Olhe para a cor mais à **esquerda embaixo**: Esses são os seus *Dias de Alerta*.")
                            
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
                                media_ads = df_xgb['investimento_ads'].tail(7).mean()
                                fat_lag = df_xgb['faturamento'].iloc[-1]

                                previsoes = []
                                for dt in datas_futuras:
                                    X_futuro = pd.DataFrame({'investimento_ads': [media_ads], 'dia_semana': [dt.dayofweek], 'fat_ontem': [fat_lag]})
                                    pred = modelo_xgb.predict(X_futuro)[0]
                                    previsoes.append(pred)
                                    fat_lag = pred

                                df_futuro = pd.DataFrame({'Data': datas_futuras, 'Faturamento Previsto (R$)': previsoes})
                                
                                # TRADUÇÃO EXECUTIVA DA PREVISÃO
                                st.info("💡 **A Bola de Cristal do seu Negócio:**\nCom base no histórico complexo de sazonalidade e na eficiência atual dos seus anúncios, o modelo desenhou a trajetória provável do seu caixa para os próximos 7 dias.")
                                
                                st.line_chart(df_futuro.set_index('Data'))
                                st.success(f"📈 Modelo validado! Mantendo a constância atual, a previsão para os próximos 7 dias é de **R$ {sum(previsoes):,.2f}**.")
                            except Exception as e:
                                st.error(f"Erro na modelagem preditiva: {e}")
                        else:
                            st.info(f"⏳ **Fase de Aprendizado da IA em Andamento ({dias_registrados}/21 dias)**")
                            st.write("O motor preditivo com **XGBoost** requer um histórico mínimo de 21 dias. Continue sincronizando seus dados para destravar a Máquina do Futuro!")
                            st.progress(min(dias_registrados / 21, 1.0))

                    st.divider()
                    st.subheader("🤖 Parecer do CFO Artificial")
                    
                    # Salva o parecer na memória da sessão para não gastar tokens extras desnecessariamente
                    with st.spinner("Analisando finanças..."):
                        prompt_cfo = f"Dados da loja: Faturamento total R${fat_total:.2f}, Investimento em Ads R${inv_total:.2f}, ROAS {roas:.2f}x. Faça uma análise executiva sobre o desempenho financeiro em 2 parágrafos curtos, focando em gargalos e oportunidades."
                        st.session_state["relatorio_gerado"] = cfo_agent.run(prompt_cfo).content
                    
                    st.write(st.session_state["relatorio_gerado"])
                    
                    st.write("")
                    
                    # --- BOTÃO DE OURO: PLANO DE AÇÃO ---
                    if st.button("🎯 Transformar Parecer em Plano de Ação", type="primary"):
                        with st.spinner("Desenhando estratégia tática e priorizando tarefas..."):
                            prompt_plano = f"Baseado neste cenário: Faturamento R${fat_total:.2f}, Ads R${inv_total:.2f}, ROAS {roas:.2f}x. O parecer anterior foi: {st.session_state['relatorio_gerado']}. \nCrie um Plano de Ação Prático de exatamente 3 passos para o dono da loja aplicar HOJE. Separe claramente em: Passo 1, Passo 2 e Passo 3. Dê exemplos ultra práticos de como ele deve agir nos criativos de anúncios, na oferta ou na velocidade do site. Seja direto, cirúrgico e agressivo para escalar lucro."
                            plano_acao = cfo_agent.run(prompt_plano).content
                            st.success("Plano Estratégico Finalizado com Sucesso!")
                            st.markdown(plano_acao)

                else:
                    st.info("Cofre vazio. Sincronize Shopify e Meta na barra lateral.")
        else:
            st.info("👋 Clique em Sincronizar Operação para rodar a análise de dados.")
