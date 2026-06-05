import streamlit as st
from supabase import create_client

def puxar_dados_nuvem(email_usuario):
    try:
        # Conecta no Supabase
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        
        # 1. Descobre o ID da empresa vinculada ao e-mail
        empresa_resp = supabase.table('empresas').select('id').eq('email_dono', email_usuario).execute()
        
        if not empresa_resp.data:
            return None # Se não achar, retorna vazio
            
        empresa_id_cliente = empresa_resp.data[0]['id']
        
        # 2. Puxa o faturamento APENAS dessa empresa
        faturamento_resp = supabase.table('faturamento_diario').select('*').eq('empresa_id', empresa_id_cliente).execute()
        
        return faturamento_resp.data
        
    except Exception as e:
        print(f"Erro: {e}")
        return None
