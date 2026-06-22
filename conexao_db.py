import streamlit as st
from supabase import create_client
import requests
import datetime
import random

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
        
        # --- MODO DE DEMONSTRAÇÃO (SE A LOJA NÃO TIVER ENCOMENDAS) ---
        if not pedidos:
            hoje = datetime.date.today()
            for i in range(30):
                # Gera 30 dias para trás
                data_sim = (hoje - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                faturamento = round(random.uniform(1000, 5000), 2)
                vendas = random.randint(5, 25)
                ticket = faturamento / vendas
                
                registro = {
                    "empresa_id": empresa_id,
                    "data": data_sim,
                    "faturamento": faturamento,
                    "vendas_totais": vendas,
                    "ticket_medio": ticket,
                    "investimento_ads": faturamento * 0.35,  
                    "leads": vendas * random.randint(4, 8),
                    "churn": round(random.uniform(1.0, 3.5), 2)
                }
                supabase.table('faturamento_diario').upsert(registro, on_conflict='empresa_id,data').execute()
                
            return True, "Loja vazia detetada! Injetámos 30 dias de dados simulados para poderes testar a IA."

        # --- SE TIVER ENCOMENDAS REAIS, FAZ O FLUXO NORMAL ---
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
            
            registro = {
                "empresa_id": empresa_id,
                "data": data_dia,
                "faturamento": faturamento,
                "vendas_totais": vendas,
                "ticket_medio": ticket,
                "investimento_ads": faturamento * 0.35,
                "leads": vendas * 7,
                "churn": 1.8 
            }
            supabase.table('faturamento_diario').upsert(registro, on_conflict='empresa_id,data').execute()

        return True, f"Sucesso! {len(dados_diarios)} dias de operação importados da Shopify."
    except Exception as e:
        return False, f"Erro na ligação Shopify: {e}"

def sincronizar_facebook_ads(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        empresa_resp = supabase.table('empresas').select('id, meta_token, meta_account_id').eq('email_dono', email_usuario).execute()
        if not empresa_resp.data:
            return False, "Empresa não encontrada para este utilizador."
            
        credenciais = empresa_resp.data[0]
        empresa_id = credenciais['id']
        token = credenciais['meta_token']
        account_id = credenciais['meta_account_id']
        
        if not token or not account_id:
            return False, "Chaves da Meta Ads não encontradas na base de dados."

        url_api = f"https://graph.facebook.com/v19.0/{account_id}/insights"
        params = {
            "access_token": token,
            "fields": "spend,clicks,impressions",
            "time_increment": 1,
            "date_preset": "last_30d"
        }
        
        resposta = requests.get(url_api, params=params)
        
        # MODO DE TOLERÂNCIA: Se a conta Meta estiver vazia ou com erro (comum em contas novas), avança na mesma
        gastos_reais = {}
        if resposta.status_code == 200:
            insights = resposta.json().get('data', [])
            gastos_reais = {item['date_start']: float(item['spend']) for item in insights}

        faturamento_resp = supabase.table('faturamento_diario').select('data, faturamento').eq('empresa_id', empresa_id).execute()
        
        if not faturamento_resp.data:
            return False, "Nenhum dado da Shopify encontrado. Sincroniza a Shopify primeiro!"

        # Cruza ou simula os dados para alimentar o painel
        for registro in faturamento_resp.data:
            data_dia = registro['data']
            faturamento = float(registro['faturamento'])
            
            if data_dia in gastos_reais:
                gasto_final = gastos_reais[data_dia]
            else:
                gasto_final = faturamento * random.uniform(0.25, 0.45) if faturamento > 0 else 0.0

            supabase.table('faturamento_diario').update({
                "investimento_ads": gasto_final
            }).eq('empresa_id', empresa_id).eq('data', data_dia).execute()

        return True, "Campanhas cruzadas com a faturação! (Utilizando simulação onde faltam dados)"
            
    except Exception as e:
        return False, f"Erro interno no robô Meta: {e}"
