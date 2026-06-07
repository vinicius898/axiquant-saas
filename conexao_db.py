import streamlit as st
from supabase import create_client
import requests
from datetime import datetime

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

# --- O ROBÔ EXECUTOR DE ETL DA SHOPIFY ---
def sincronizar_loja_shopify(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # 1. Busca as credenciais da empresa no banco
        empresa_resp = supabase.table('empresas').select('id, shopify_url, shopify_token').eq('email_dono', email_usuario).execute()
        if not empresa_resp.data:
            return False, "Empresa não vinculada a este e-mail."
            
        empresa = empresa_resp.data[0]
        empresa_id = empresa['id']
        url_loja = empresa['shopify_url']
        token = empresa['shopify_token']
        
        if not url_loja or not token:
            return False, "Credenciais da Shopify ausentes no Supabase."

        # 2. Coleta os pedidos na API da Shopify
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        url_api = f"https://{url_loja}/admin/api/2024-01/orders.json?status=any&limit=250"
        
        resposta = requests.get(url_api, headers=headers)
        if resposta.status_code != 200:
            return False, f"Erro Shopify: {resposta.status_code}"
            
        pedidos = resposta.json().get('orders', [])
        if not pedidos:
            return True, "Conexão bem-sucedida, mas nenhum pedido foi encontrado na loja."

        # 3. TRANSFORMAÇÃO: Agrupa os pedidos por dia (Matemática de Ingestão)
        dados_diarios = {}
        
        for pedido in pedidos:
            # Extrai apenas a data (AAAA-MM-DD) desconsiderando a hora
            data_str = pedido['created_at'].split('T')[0]
            valor_pedido = float(pedido.get('current_total_price', pedido.get('total_price', 0)))
            
            if data_str not in dados_diarios:
                dados_diarios[data_str] = {"faturamento": 0.0, "vendas_totais": 0}
                
            dados_diarios[data_str]["faturamento"] += valor_pedido
            dados_diarios[data_str]["vendas_totais"] += 1

        # 4. CARGA: Salva ou Atualiza (Upsert) cada dia no Supabase
        linhas_processadas = 0
        for data_dia, metricas in dados_diarios.items():
            faturamento = metricas["faturamento"]
            vendas = metricas["vendas_totais"]
            ticket = faturamento / vendas if vendas > 0 else 0
            
            # placeholders inteligentes para Ads e Leads para alimentar o Cérebro Triplo
            simulacao_ads = faturamento * 0.35  
            simulacao_leads = vendas * 7
            simulacao_churn = 1.8 

            # Monta o registro estruturado
            registro = {
                "empresa_id": empresa_id,
                "data": data_dia,
                "faturamento": faturamento,
                "vendas_totais": vendas,
                "ticket_medio": ticket,
                "investimento_ads": simulacao_ads,
                "leads": simulacao_leads,
                "churn": simulacao_churn
            }
            
            # O comando 'upsert' insere se o dia não existir, ou atualiza se o dia já existir
            supabase.table('faturamento_diario').upsert(
                registro, 
                on_conflict='empresa_id,data'
            ).execute()
            linhas_processadas += 1

        return True, f"Sucesso! {linhas_processadas} dias de operação importados e sincronizados."

    except Exception as e:
        return False, f"Erro no encanamento: {e}"
