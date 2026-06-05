import streamlit as st
from supabase import create_client

def puxar_dados_nuvem(email_usuario):
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # 1. Descobrir qual é o ID da empresa vinculada a este e-mail logado
        empresa_resp = supabase.table('empresas').select('id').eq('email_dono', email_usuario).execute()
        
        if not empresa_resp.data:
            return None # Se não achar a empresa, barra o acesso aos dados
            
        empresa_id_cliente = empresa_resp.data[0]['id']
        
        # 2. Puxar o faturamento APENAS dessa empresa específica
        faturamento_resp = supabase.table('faturamento_diario').select('*').eq('empresa_id', empresa_id_cliente).execute()
        
        return faturamento_resp.data
    except Exception as e:
        st.error(f"Erro na conexão com o banco de dados: {e}")
        return None
