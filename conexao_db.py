import streamlit as st
from supabase import create_client
import requests # A biblioteca que faz o seu app viajar pela internet

def puxar_dados_nuvem(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        empresa_resp = supabase.table('empresas').select('id').eq('email_dono', email_usuario).execute()
        
        if not empresa_resp.data:
            return None
            
        empresa_id_cliente = empresa_resp.data[0]['id']
        faturamento_resp = supabase.table('faturamento_diario').select('*').eq('empresa_id', empresa_id_cliente).execute()
        
        return faturamento_resp.data
    except Exception as e:
        print(f"Erro: {e}")
        return None

# --- O NOVO ROBÔ DA SHOPIFY ---
def conectar_api_shopify(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # 1. Pega as chaves no cofre do Supabase
        empresa_resp = supabase.table('empresas').select('shopify_url, shopify_token').eq('email_dono', email_usuario).execute()
        
        if not empresa_resp.data:
            return None, "Empresa não encontrada."
            
        credenciais = empresa_resp.data[0]
        url_loja = credenciais['shopify_url']
        token = credenciais['shopify_token']
        
        if not url_loja or not token:
            return None, "Chaves da Shopify não encontradas no banco."

        # 2. Bate na porta da Shopify
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }
        
        # URL oficial da API para puxar os pedidos (status=any para pegar as vendas de teste)
        url_api = f"https://{url_loja}/admin/api/2024-01/orders.json?status=any"
        
        resposta = requests.get(url_api, headers=headers)
        
        if resposta.status_code == 200:
            pedidos = resposta.json().get('orders', [])
            return pedidos, "Sucesso"
        else:
            return None, f"Erro da Shopify: {resposta.text}"
            
    except Exception as e:
        return None, f"Erro interno do robô: {e}"
