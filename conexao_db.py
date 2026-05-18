import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# Tenta carregar o arquivo .env (útil apenas quando rodar no seu PC local)
load_dotenv(override=True)

# 1. Função Cofre: Busca na Nuvem (st.secrets), se falhar, busca no PC (os.getenv)


def buscar_chave(nome):
    try:
        # Tenta abrir o cofre da nuvem primeiro
        return st.secrets[nome]
    except:
        # Se der erro, procura no sistema do computador
        return os.getenv(nome)


# 2. Injeta as chaves no sistema operacional (A IA e o Banco precisam disso na nuvem)
chave_groq = buscar_chave("GROQ_API_KEY")
if chave_groq:
    os.environ["GROQ_API_KEY"] = chave_groq

url_bruta = buscar_chave("SUPABASE_URL")
chave_bruta = buscar_chave("SUPABASE_KEY")

if not url_bruta:
    # Trava de segurança para avisar se o cofre estiver trancado
    raise ValueError(
        "Chaves não encontradas! O Streamlit Cloud não encontrou as senhas nos Secrets.")

# Formata a URL do Supabase para evitar erros
SUPABASE_URL = url_bruta.replace(
    "/rest/v1/", "").replace("/rest/v1", "").rstrip("/")
SUPABASE_KEY = chave_bruta


def puxar_dados_nuvem():
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Puxa o ID da empresa (se não achar, usa '1' como padrão)
        empresa_id = buscar_chave(
            "676e1310-117b-4053-8460-f2d131f679c8") or "1"

        resposta = supabase.table('faturamento_diario').select(
            '*').eq('empresa_id', int(empresa_id)).order('data', desc=False).execute()

        if resposta.data:
            return pd.DataFrame(resposta.data)
        else:
            return None
    except Exception as e:
        print(f"Erro ao conectar com o Supabase: {e}")
        return None
