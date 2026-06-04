import streamlit as st
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from conexao_db import puxar_dados_nuvem
from agno.agent import Agent
from agno.models.groq import Groq
from dotenv import load_dotenv
import os

# 1. Configuração da Página
st.set_page_config(page_title="AxiQuant Admin", layout="wide", page_icon="💎")

st.title("📊 Painel de Inteligência Executiva (Cérebro Triplo)")
st.markdown("Visão preditiva, prescritiva e descritiva alimentada por Machine Learning.")

# 2. Inicializar Agente IA (CFO)
import os
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

cfo_agent = Agent(
    model=Groq(id="llama3-70b-8192"),
    description="Você é um CFO sênior de um fundo quantitativo. Seja analítico e direto."
)
# 3. Motor Principal
if st.sidebar.button("☁️ Sincronizar Operação", type="primary"):
    with st.spinner("Conectando ao banco de dados e rodando Machine Learning..."):
        dados = puxar_dados_nuvem()
        
        if dados is not None and len(dados) > 0:
            df = pd.DataFrame(dados)
            
            # Limpeza e Conversão
            df['data'] = pd.to_datetime(df['data'])
            cols_numericas = ['leads', 'investimento_ads', 'ticket_medio', 'vendas_totais', 'churn', 'faturamento']
            for col in cols_numericas:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.sort_values('data').dropna()
            
            # --- KPIs ---
            st.success("Dados Sincronizados e Processados!")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Faturamento Total", f"R$ {df['faturamento'].sum():,.2f}")
            col2.metric("Investimento Total (Ads)", f"R$ {df['investimento_ads'].sum():,.2f}")
            col3.metric("Ticket Médio", f"R$ {df['ticket_medio'].mean():,.2f}")
            col4.metric("Dias Analisados", len(df))
            
            st.divider()

            # --- O CÉREBRO TRIPLO ---
            st.header("🧠 Motores de Machine Learning")
            tab1, tab2, tab3 = st.tabs(["Regressão (Causas)", "Classificação (Importância)", "Clusterização (Padrões)"])
            
            peso_ads = 0
            importancias_lista = ""

            # MOTOR 1: REGRESSÃO OLS
            with tab1:
                st.markdown("### 🔍 Regressão OLS (Qual alavanca move o dinheiro?)")
                try:
                    X_reg = df[['investimento_ads', 'leads', 'ticket_medio']]
                    y_reg = df['faturamento']
                    X_reg = sm.add_constant(X_reg)
                    modelo_ols = sm.OLS(y_reg, X_reg).fit()
                    
                    peso_ads = modelo_ols.params.get('investimento_ads', 0)
                    
                    st.write("Peso Matemático de cada Variável:")
                    st.dataframe(pd.DataFrame({
                        "Variável": modelo_ols.params.index,
                        "Peso (Coeficiente)": modelo_ols.params.values
                    }).style.format({"Peso (Coeficiente)": "{:.2f}"}))
                    st.info(f"💡 **Insight:** Cada R$ 1,00 colocado em Ads gera um peso de {peso_ads:.2f} no faturamento total, assumindo o resto constante.")
                except Exception as e:
                    st.error(f"Erro no motor OLS: {e}")

            # MOTOR 2: RANDOM FOREST
            with tab2:
                st.markdown("### 🎯 Classificação (O que dita um dia de Alta Performance?)")
                try:
                    mediana = df['faturamento'].median()
                    df['alta_performance'] = (df['faturamento'] > mediana).astype(int)
                    
                    X_clf = df[['investimento_ads', 'leads', 'ticket_medio', 'churn']]
                    y_clf = df['alta_performance']
                    
                    rf = RandomForestClassifier(random_state=42, n_estimators=50)
                    rf.fit(X_clf, y_clf)
                    
                    importancias = pd.DataFrame({
                        'Variável': X_clf.columns,
                        'Poder de Decisão (%)': rf.feature_importances_ * 100
                    }).sort_values('Poder de Decisão (%)', ascending=False)
                    
                    importancias_lista = importancias.to_dict('records')
                    
                    st.bar_chart(importancias.set_index('Variável'))
                    st.info("💡 **Insight:** A árvore de decisão avaliou que a variável no topo do gráfico é a verdadeira responsável por definir se o dia dará muito lucro ou não.")
                except Exception as e:
                    st.error(f"Erro na classificação: {e}")

            # MOTOR 3: K-MEANS
            with tab3:
                st.markdown("### 🧩 Agrupamento Não Supervisionado (Clusters)")
                try:
                    X_clust = df[['investimento_ads', 'faturamento', 'churn']]
                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X_clust)
                    
                    kmeans = KMeans(n_clusters=3, random_state=42)
                    df['Cluster'] = kmeans.fit_predict(X_scaled)
                    df['Cluster'] = df['Cluster'].astype(str) # Converter para string para o gráfico diferenciar cores
                    
                    st.scatter_chart(df, x='investimento_ads', y='faturamento', color='Cluster')
                    st.info("💡 **Insight:** A IA agrupou os dias de operação em 3 tribos (Cores). Procure por pontos onde o investimento (eixo X) é baixo, mas o faturamento (eixo Y) é alto!")
                except Exception as e:
                    st.error(f"Erro na clusterização: {e}")

            st.divider()

            # --- PARECER DO CFO ---
            st.subheader("🤖 Parecer do CFO Artificial")
            if cfo_agent:
                with st.spinner("O CFO está analisando as matrizes matemáticas..."):
                    prompt_cfo = f"""
                    Aja como o Arquiteto Chefe Financeiro (CFO) de um negócio digital de alta performance.
                    Aqui estão os dados globais dos últimos {len(df)} dias:
                    - Faturamento: R$ {df['faturamento'].sum():.2f}
                    - Gasto em Ads: R$ {df['investimento_ads'].sum():.2f}
                    
                    Seus motores de Machine Learning relataram:
                    1. O multiplicador linear do Investimento em Ads é {peso_ads:.2f}.
                    2. A árvore de decisão aponta a seguinte hierarquia de importância para o sucesso da operação: {importancias_lista}.
                    
                    Escreva um relatório executivo de 2 parágrafos. Diga o que está ótimo, o que é um risco silencioso, e sugira uma tática clara. Seja analítico e direto.
                    """
                    resposta = cfo_agent.run(prompt_cfo).content
                    st.write(resposta)
            else:
                st.warning("API Key do Groq ausente.")
                
        else:
            st.error("Nenhum dado encontrado no Supabase.")
else:
    st.info("👋 O Motor Triplo está pronto. Clique em Sincronizar na barra lateral para dar a ignição.")
