import streamlit as st
import pandas as pd
import urllib.parse
import requests

st.set_page_config(page_title="Dashboard NR-01", layout="wide")

# =========================================================================
ID_DA_PLANILHA = "1klYEryQRKGUjTN7XOHf9fqprRQTqcYUcEIu0TIfQtc4"
NOME_DA_ABA = "PLANILHA TÉCNICO" 
# =========================================================================

# Função para garantir que o Streamlit leia os dados novos toda vez
@st.cache_data(ttl=0)
def carregar_dados():
    nome_aba_codificado = urllib.parse.quote(NOME_DA_ABA)
    url = f"https://docs.google.com/spreadsheets/d/1klYEryQRKGUjTN7XOHf9fqprRQTqcYUcEIu0TIfQtc4/gviz/tq?tqx=out:csv&sheet=BB"
    df = pd.read_csv(url)
    df.columns = [col.strip() for col in df.columns]
    return df

def buscar_nome_empresa(cnpj):
    # Limpa o CNPJ: mantém apenas números
    cnpj_limpo = "".join(filter(str.isdigit, str(cnpj)))
    if not cnpj_limpo: return None
    try:
        url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
        resposta = requests.get(url, timeout=10)
        if resposta.status_code == 200:
            return resposta.json().get("nome")
    except:
        pass
    return None

def obter_classificacao_risco(media):
    if media <= 1.99: return "Risco Irrelevante", "#2E7D32", "🟢"
    elif 2.0 <= media <= 2.99: return "Risco Baixo", "#4CAF50", "🟢"
    elif 3.0 <= media <= 3.99: return "Risco Médio", "#FF9800", "🟡"
    elif 4.0 <= media <= 4.5: return "Risco Alto", "#E53935", "🔴"
    else: return "Risco Crítico", "#8B0000", "🚨"

# --- EXECUÇÃO ---
try:
    df_completo = carregar_dados()
    col_data = df_completo.columns[0]
    col_cnpj = df_completo.columns[1]
    
    # Filtro
    cnpj_busca = st.query_params.get("cnpj", "").strip()
    
    if cnpj_busca:
        # Filtra o dataframe original
        df_original = df_completo[df_completo[col_cnpj].astype(str).str.strip() == cnpj_busca].copy()
        
        if df_original.empty:
            st.warning(f"CNPJ {cnpj_busca} não encontrado.")
            df_original = df_completo
        else:
            nome_empresa = buscar_nome_empresa(cnpj_busca)
            st.success(f"🏢 Empresa: {nome_empresa or 'Não identificada'} ({cnpj_busca})")
    else:
        df_original = df_completo
        st.info("📊 Visão geral de todas as empresas.")

    # Processamento dos números
    colunas_perguntas = list(df_original.columns[2:42])
    df_numerico = df_original[colunas_perguntas].apply(pd.to_numeric, errors='coerce')
    
    # Gráfico de Distribuição Fixo
    st.subheader("📊 Distribuição de Respostas (Filtrado)")
    
    # Conta apenas os valores válidos (1 a 5)
    contagens = df_numerico.stack().value_counts().sort_index()
    
    # Cria o dataframe para o gráfico garantindo que todas as notas de 1 a 5 apareçam
    df_grafico = pd.DataFrame({
        "Nota": ["Risco Irrelevante (1)", "Risco Baixo (2)", "Risco Médio (3)", "Risco Alto (4)", "Risco Crítico (5)"],
        "Qtd": [contagens.get(1, 0), contagens.get(2, 0), contagens.get(3, 0), contagens.get(4, 0), contagens.get(5, 0)]
    })
    
    st.bar_chart(df_grafico.set_index("Nota"), color="#4B70DD")

    # Média e outros cards
    media_geral = df_numerico.mean().mean()
    nome_risco, cor_risco, emoji_risco = obter_classificacao_risco(media_geral)
    
    # Exibir métricas e planos (mantive a lógica que funcionou antes)
    # ... (restante do seu código original de exibição)

except Exception as e:
    st.error(f"Erro no processamento: {e}")
