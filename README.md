# AxiQuant: Abordagens de Machine Learning e Econometria na Avaliação de Desempenho de Campanhas de Marketing Digital

## 📌 Apresentação do Projeto (Proposta de TCC)

Prezado(a) Orientador(a),

Este repositório documenta o desenvolvimento do **AxiQuant**, um projeto prático que serve como base empírica para o Trabalho de Conclusão de Curso (TCC) em Bacharelado em Estatística. 

O escopo do trabalho visa solucionar um problema crônico no mercado de negócios digitais: a atribuição correta de receita e a avaliação do Retorno sobre Investimento (ROI) em campanhas de marketing. Em ambientes reais, variáveis como gastos com anúncios (Tráfego Pago) e alcance de conteúdo (Tráfego Orgânico) frequentemente interagem de forma complexa, tornando análises simplistas (como o ROAS direto da plataforma) enviesadas.

O objetivo desta pesquisa aplicada é desenvolver e produtizar um framework estatístico que avalie campanhas de forma isolada, agrupando-as por perfis de eficiência e simulando retornos esperados, encapsulando toda a complexidade matemática em uma aplicação web (SaaS) acessível para tomadores de decisão.

---

## 🎯 Objetivos

### Objetivo Geral
Desenvolver um modelo estatístico e computacional para atribuição e otimização de Retorno de Campanhas de Marketing, utilizando um banco de dados real e anonimizado de campanhas digitais.

### Objetivos Específicos
1. **Atribuição de Margem:** Isolar o efeito marginal de diferentes canais de aquisição sobre a Margem de Contribuição de Marketing (MCM).
2. **Segmentação Multivariada:** Aplicar métodos não supervisionados para identificar padrões latentes de sucesso ou falha em campanhas históricas.
3. **Modelagem Preditiva:** Construir um simulador que permita estimar o lucro de novas campanhas com base em orçamentos e alcances projetados.
4. **Produtização (Data App):** Implementar o modelo em uma arquitetura de software funcional, utilizando LLMs (Large Language Models) apenas para a tradução dos resultados matemáticos em linguagem de negócios.

---

## 🔬 Metodologia Estatística Aplicada

Para garantir o rigor científico, o projeto afasta-se de dados simulados ou heurísticas manuais, apoiando-se em processos validados:

### 1. Base de Dados
A pesquisa utiliza o dataset público **`KAG_conversion_data.csv`** (disponibilizado via Kaggle), contendo 1.143 observações reais de campanhas no Facebook Ads. 
* A granularidade da análise é a **nível de campanha** (cross-sectional), e não em séries temporais contínuas.
* **Variáveis de Interesse:** Gastos na campanha (`Spent`), Visualizações (`Impressions`), Engajamento (`Clicks`) e Vendas (`Approved_Conversion`).
* **Variável Resposta (Target):** Margem de Contribuição de Marketing (MCM), definida pela receita gerada subtraída do custo da campanha.

### 2. Inferência e Tratamento de Multicolinearidade (Bastidores Metodológicos)
A estimação dos efeitos marginais baseia-se inicialmente em Regressão Linear Múltipla (OLS). Contudo, devido à natureza dos dados de marketing (onde investimento e alcance crescem simultaneamente), o pipeline do modelo realiza um diagnóstico formal de estabilidade:
* O sistema calcula automaticamente o **Fator de Inflação da Variância (VIF)** para cada variável independente.
* Caso o diagnóstico aponte multicolinearidade severa ($VIF > 5$), a aplicação inviabiliza os estimadores OLS e converge silenciosamente para uma **Regressão Ridge (Penalização L2)**.
* A escolha do parâmetro de penalização ($\lambda^*$) não é manual. O sistema utiliza a rotina `RidgeCV` para encontrar o hiperparâmetro ótimo através de Validação Cruzada, minimizando o erro de generalização antes de retornar os coeficientes finais.

### 3. Modelagem de Mistura Gaussiana (GMM)
Para a classificação de campanhas, o projeto utiliza Modelos de Mistura Gaussiana (GMM). Diferente de métodos rígidos como K-Means, o GMM permite a clusterização elíptica e probabilística das campanhas, segmentando-as matematicamente em três estados de densidade: Campanhas Ineficientes, Estáveis e de Alto Retorno.

### 4. Árvores de Decisão e Regressão Estocástica
* **Importância de Variáveis:** O algoritmo `RandomForestClassifier` é empregado para medir o Peso/Gini Impurity das variáveis na determinação da superação da mediana de lucro.
* **Previsão de Cenários:** Um algoritmo de Gradient Boosting (`XGBoost`) atua como regressor para prever o MCM de campanhas futuras dadas novas entradas de investimento e alcance esperado.

---

## 💻 Arquitetura de Software e Tecnologias

O projeto foi construído para operar em nuvem, separando a camada de persistência de dados da camada de processamento analítico.

* **Frontend e Visualização:** `Streamlit`, `Plotly` (renderização baseada na gramática de gráficos do *ggplot2*).
* **Engenharia e Processamento de Dados:** `Pandas`, `NumPy`.
* **Modelagem Estatística e Machine Learning:** `Statsmodels` (Inferência e VIF), `Scikit-Learn` (RidgeCV, RF, GMM, StandardScaler), `XGBoost`.
* **Banco de Dados:** `Supabase` (PostgreSQL com RLS e isolamento multi-tenant).
* **Camada de Interpretação (IA):** Integração com `Agno` e `Groq API` (modelo *Llama-3.3-70b-versatile*) para redigir pareceres gerenciais baseados exclusivamente nas saídas numéricas do modelo.

---

## ⚙️ Documentação de Uso e Instalação Local

Para testar a aplicação e auditar os modelos estatísticos implementados, siga os passos abaixo:

**1. Clone o repositório:**
```bash
git clone [https://github.com/seu-usuario/axiquant.git](https://github.com/seu-usuario/axiquant.git)
cd axiquant

**2. Instale as dependências:**
```bash

pip install streamlit pandas numpy statsmodels scikit-learn xgboost plotly supabase openai agno
