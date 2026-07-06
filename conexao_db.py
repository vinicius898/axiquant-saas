import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Inicialização do Cliente Supabase (Conectando via Secrets do Streamlit)
@st.cache_resource
def iniciar_conexao():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = iniciar_conexao()

# ==========================================
# MÓDULOS DE SINCRONIZAÇÃO (Integrações Externas)
# ==========================================

def sincronizar_loja_shopify(email_dono):
    """
    Função de sincronização com a Shopify API.
    (Atualmente operando em modo de simulação/mock para fins de MVP)
    """
    try:
        # Aqui no futuro entrará o requests.get() para a API da Shopify
        return True, "Pedidos da Shopify sincronizados com sucesso."
    except Exception as e:
        return False, f"Erro de conexão com Shopify: {e}"

def sincronizar_facebook_ads(email_dono):
    """
    Função de sincronização com a Meta Graph API.
    (Atualmente operando em modo de simulação/mock para fins de MVP)
    """
    try:
        # Aqui no futuro entrará o requests.get() para a API do Facebook
        return True, "Métricas do Meta Ads sincronizadas com sucesso."
    except Exception as e:
        return False, f"Erro de conexão com Facebook: {e}"

# ==========================================
# MÓDULO DE LEITURA E ENGENHARIA DE DADOS
# ==========================================

def puxar_dados_nuvem(email_dono):
    """
    Puxa os dados financeiros e de mídias sociais do Supabase
    e funde as duas tabelas perfeitamente usando a Data como elo (INNER JOIN via Pandas).
    """
    try:
        # 1. Busca o ID numérico da empresa com base no e-mail do usuário logado
        empresa_resp = supabase.table('empresas').select('id').eq('email_dono', email_dono).execute()
        if not empresa_resp.data: 
            return None
        emp_id = empresa_resp.data[0]['id']

        # 2. Puxa as duas tabelas separadamente do banco de dados
        fat_resp = supabase.table('faturamento_diario').select('*').eq('empresa_id', emp_id).execute()
        mkt_resp = supabase.table('marketing_diario').select('*').eq('empresa_id', emp_id).execute()
        
        # Se não houver faturamento nenhum, nem adianta mostrar gráficos
        if not fat_resp.data: 
            return None
        
        # Transforma a resposta do banco em uma tabela inteligente do Pandas
        df_fat = pd.DataFrame(fat_resp.data)
        
        # 3. Se existirem dados de mídias sociais (marketing_diario), fazemos a fusão
        if mkt_resp.data:
            df_mkt = pd.DataFrame(mkt_resp.data)
            
            # TRAVA DE SEGURANÇA: Garante que as datas estão no mesmo formato matemático
            df_fat['data'] = pd.to_datetime(df_fat['data'])
            df_mkt['data'] = pd.to_datetime(df_mkt['data'])
            
            # O JOIN: Cola as colunas de social media do lado das finanças onde a data bater
            df_final = pd.merge(df_fat, df_mkt, on=['empresa_id', 'data'], how='left')
            
            # Se a pessoa teve venda num dia, mas não postou nada no Instagram,
            # os campos de views/engajamento ficariam nulos (NaN). Preenchemos com 0.
            df_final = df_final.fillna(0)
            
            # Devolve os dados prontos para o dashboard.py ler
            return df_final.to_dict('records')
            
        # Se a tabela de marketing estiver vazia, retorna só as finanças para não quebrar o sistema
        return df_fat.to_dict('records')
        
    except Exception as e:
        print(f"Erro crasso ao puxar ou fundir dados combinados: {e}")
        return None
