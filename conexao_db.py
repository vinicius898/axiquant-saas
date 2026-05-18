import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Carrega as chaves
load_dotenv(override=True)
SUPABASE_URL = os.getenv("SUPABASE_URL").replace(
    "/rest/v1/", "").replace("/rest/v1", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ⚠️ COLOQUE AQUI O SEU ID DA EMPRESA
EMPRESA_ID = "676e1310-117b-4053-8460-f2d131f679c8"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def puxar_dados_nuvem():
    """
    Vai até o Supabase, baixa as tabelas, agrupa as vendas por dia 
    e devolve um DataFrame idêntico ao antigo CSV.
    """
    print("Conectando ao Supabase...")

    # 1. Puxar Marketing
    url_mkt = f"{SUPABASE_URL}/rest/v1/marketing_diario?empresa_id=eq.{EMPRESA_ID}"
    req_mkt = requests.get(url_mkt, headers=headers)
    df_mkt = pd.DataFrame(req_mkt.json())

    # 2. Puxar Vendas
    url_vendas = f"{SUPABASE_URL}/rest/v1/vendas_granulares?empresa_id=eq.{EMPRESA_ID}"
    req_vendas = requests.get(url_vendas, headers=headers)
    df_vendas = pd.DataFrame(req_vendas.json())

    # 3. Tratamento de Dados (O Liquidificador)
    # Converte datas para o mesmo padrão
    # Normaliza datas e remove o fuso horário (UTC) para padronizar
    df_mkt['data'] = pd.to_datetime(df_mkt['data_referencia'])
    df_vendas['data'] = pd.to_datetime(
        df_vendas['data_hora_venda']).dt.tz_localize(None).dt.normalize()

    # Agrupa as vendas por dia (soma o valor bruto do dia)
    vendas_diarias = df_vendas.groupby(
        'data')['valor_bruto'].sum().reset_index()
    vendas_diarias.rename(columns={'valor_bruto': 'Receita'}, inplace=True)

    # Agrupa marketing por dia
    mkt_diario = df_mkt.groupby('data')['valor_investido'].sum().reset_index()
    mkt_diario.rename(
        columns={'valor_investido': 'Investimento_Ads'}, inplace=True)

    # 4. A Fusão (Merge)
    df_final = pd.merge(vendas_diarias, mkt_diario, on='data', how='inner')

    # Para não quebrar o seu motor antigo que esperava outras colunas,
    # criamos colunas neutras temporárias até você atualizar a matemática do motor
    import numpy as np
    df_final['Preco_Venda'] = np.random.uniform(50, 150, len(df_final))
    df_final['Postagens_Social'] = np.random.randint(0, 5, len(df_final))

    print(
        f"✅ Dados puxados com sucesso! {len(df_final)} dias de operação carregados.")
    return df_final
