# 💎 AxiQuant SaaS: O CFO Artificial Quantitativo

O **AxiQuant** é um software (SaaS) focado em **Marketing Mix Modeling (MMM)** e análise de dados financeiros para e-commerces e negócios digitais. Utilizando algoritmos de Machine Learning e Inteligência Artificial Generativa, o sistema audita o histórico de tráfego pago e orgânico, isola o retorno real (ROI) de cada canal e projeta o fluxo de caixa futuro.

Este projeto também atua como base empírica para um **Trabalho de Conclusão de Curso (TCC) em Bacharelado em Estatística**, focado na resolução de multicolinearidade em dados de marketing através de Regressão Penalizada (Ridge) e Modelagem Preditiva.

---

## 🚀 Arquitetura e Tecnologias (Tech Stack)

* **Frontend & Dashboard:** Streamlit, Plotly (Visualização padrão `ggplot2`).
* **Backend & Banco de Dados:** Supabase (PostgreSQL), Python.
* **Engenharia de Dados (ETL):** Pandas, NumPy, conexão direta via GitHub Raw (Kaggle Datasets).
* **Machine Learning & Estatística:**
  * `statsmodels` (Regressão OLS Padrão)
  * `scikit-learn` (Regressão Ridge, Random Forest, Gaussian Mixture Models - GMM)
  * `xgboost` (Regressão Estocástica de Séries Temporais)
* **Inteligência Artificial (LLM):** Agentes Autônomos via `agno` rodando o modelo `Llama-3.3-70b-versatile` através da API da **Groq** (Alta velocidade de inferência).

---

## 🧠 Inteligência Estatística Implementada (Até o momento)

### 1. Injeção de Dados Reais (Data Pipeline)
O sistema abandonou simulações (`random.normal`) e foi integrado a um banco de dados real do mercado. Através do script `importar_kaggle.py`, o banco de dados PostgreSQL (Supabase) consome, traduz e injeta mais de 1.100 campanhas auditadas da Meta (arquivo *KAG_conversion_data.csv* do Kaggle), criando um histórico robusto e livre de vieses de amostragem sintética.

### 2. Resolução de Multicolinearidade (AutoML Híbrido)
Dados reais de marketing sofrem de multicolinearidade natural (gastos com anúncios e alcance orgânico crescem juntos).
* O sistema tenta rodar uma **Regressão OLS** padrão.
* Se os pesos (Betas) retornarem negativos (indicando distorção estatística), o sistema automaticamente aplica uma **Regressão Ridge (Regularização L2)** nos bastidores.
* Os dados são padronizados (`StandardScaler`), a variância é penalizada, e os coeficientes são revertidos matematicamente para a escala financeira original (R$), entregando o valor incremental exato de cada visualização orgânica e de cada Real investido em Ads.

### 3. Clusterização de Risco de Caixa (GMM)
Substituindo métricas de vaidade simples, o sistema utiliza **Gaussian Mixture Models (GMM)** para agrupar o histórico em elipses de densidade probabilística, classificando os dias da operação em "Dias de Ouro", "Dias Estáveis" e "Dias de Risco" com base na eficiência do capital investido versus Margem de Contribuição.

### 4. Bússola de Vendas (XGBoost)
Um modelo preditivo avalia a sazonalidade e a memória financeira da semana anterior para prever a **Margem de Contribuição de Marketing (MCM)** dos próximos 7 dias.

### 5. Consultor Executivo (IA Generativa Avançada)
Um agente LLM conectado ao modelo Llama-3 consome os coeficientes matemáticos da Regressão Ridge e do GMM, traduzindo-os em um parecer executivo e gerando um **Plano de Ação Tático** em linguagem de negócios, sem expor a complexidade econométrica ao lojista/usuário final.

---

## 🛠️ Como Executar o Projeto Localmente

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/axiquant.git](https://github.com/seu-usuario/axiquant.git)
   cd axiquant


   
