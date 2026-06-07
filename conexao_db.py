import streamlit as st
from supabase import create_client
import requests

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

def sincronizar_loja_shopify(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        empresa_resp = supabase.table('empresas').select('id, shopify_url, shopify_token').eq('email_dono', email_usuario).execute()
        if not empresa_resp.data:
            return False, "Empresa não vinculada a este e-mail."
            
        empresa = empresa_resp.data[0]
        empresa_id = empresa['id']
        url_loja = empresa['shopify_url']
        token = empresa['shopify_token']
        
        if not url_loja or not token:
            return False, "Credenciais da Shopify ausentes no Supabase."

        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        url_api = f"https://{url_loja}/admin/api/2024-01/orders.json?status=any&limit=250"
        
        resposta = requests.get(url_api, headers=headers)
        if resposta.status_code != 200:
            return False, f"Erro Shopify: {resposta.status_code}"
            
        pedidos = resposta.json().get('orders', [])
        if not pedidos:
            return True, "Conexão bem-sucedida, mas nenhum pedido foi encontrado na loja."

        dados_diarios = {}
        for pedido in pedidos:
            data_str = pedido['created_at'].split('T')[0]
            valor_pedido = float(pedido.get('current_total_price', pedido.get('total_price', 0)))
            
            if data_str not in dados_diarios:
                dados_diarios[data_str] = {"faturamento": 0.0, "vendas_totais": 0}
                
            dados_diarios[data_str]["faturamento"] += valor_pedido
            dados_diarios[data_str]["vendas_totais"] += 1

        for data_dia, metricas in dados_diarios.items():
            faturamento = metricas["faturamento"]
            vendas = metricas["vendas_totais"]
            ticket = faturamento / vendas if vendas > 0 else 0
            
            simulacao_ads = faturamento * 0.35  
            simulacao_leads = vendas * 7
            simulacao_churn = 1.8 

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
            
            supabase.table('faturamento_diario').upsert(registro, on_conflict='empresa_id,data').execute()

        return True, f"Sucesso! {len(dados_diarios)} dias de operação importados da Shopify."
    except Exception as e:
        return False, f"Erro no encanamento: {e}"


# --- O NOVO ROBÔ DA API DO FACEBOOK/META ADS ---
def sincronizar_facebook_ads(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # 1. Puxa as credenciais da Meta salvas no Supabase
        empresa_resp = supabase.table('empresas').select('id, meta_token, meta_account_id').eq('email_dono', email_usuario).execute()
        if not empresa_resp.data:
            return False, "Empresa não encontrada para este usuário."
            
        credenciais = empresa_resp.data[0]
        empresa_id = credenciais['id']
        token = credenciais['meta_token']
        account_id = credenciais['meta_account_id']
        
        if not token or not account_id:
            return False, "Chaves da Meta Ads não encontradas no banco."

        # 2. Faz a chamada oficial na Graph API da Meta pedindo gastos diários
        url_api = f"https://graph.facebook.com/v19.0/{account_id}/insights"
        params = {
            "access_token": token,
            "fields": "spend,clicks,impressions",
            "time_increment": 1,
            "date_preset": "last_30d"
        }
        
        resposta = requests.get(url_api, params=params)
        
        if resposta.status_code != 200:
            erro_msg = resposta.json().get('error', {}).get('message', 'Erro desconhecido')
            return False, f"Erro na API da Meta: {erro_msg}"
            
        insights = resposta.json().get('data', [])
        gastos_reais = {item['date_start']: float(item['spend']) for item in insights}

        # 3. CRUZA OS DADOS: Pega os dias existentes da Shopify e atualiza os gastos
        faturamento_resp = supabase.table('faturamento_diario').select('data, faturamento').eq('empresa_id', empresa_id).execute()
        
        if not faturamento_resp.data:
            return False, "Nenhum dado da Shopify encontrado. Sincronize a Shopify primeiro!"

        for registro in faturamento_resp.data:
            data_dia = registro['data']
            faturamento = float(registro['faturamento'])
            
            # Se houver gasto real na Meta, usamos. Se não, calibramos a simulação
            if data_dia in gastos_reais:
                gasto_final = gastos_reais[data_dia]
            else:
                gasto_final = faturamento * 0.36 if faturamento > 0 else 0.0

            # Atualiza APENAS a coluna de anúncios daquele dia específico
            supabase.table('faturamento_diario').update({
                "investimento_ads": gasto_final
            }).eq('empresa_id', empresa_id).eq('data', data_dia).execute()

        if len(insights) > 0:
            return True, f"Sucesso! {len(insights)} dias de campanhas reais integrados ao faturamento!"
        else:
            return True, "Chave Validada! Modo Calibração Ativado: Gastos simulados de anúncios injetados com sucesso."
            
    except Exception as e:
        return False, f"Erro interno no robô Meta: {e}"
