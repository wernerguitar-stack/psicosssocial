import streamlit as st
import pandas as pd
import urllib.parse

# 1. Configuração da página do site
st.set_page_config(page_title="Dashboard NR-01", layout="wide")

# --- ALTERAÇÃO 1: Novo Nome do Painel ---
st.title("📊 Dashboard de avaliação dos riscos do Psicossocial NR-01")

# =========================================================================
# ID DA SUA PLANILHA GOOGLE
ID_DA_PLANILHA = "1klYEryQRKGUjTN7XOHf9fqprRQTqcYUcEIu0TIfQtc4"
NOME_DA_ABA = "PLANILHA TÉCNICO" 
# =========================================================================

nome_aba_codificado = urllib.parse.quote(NOME_DA_ABA)
URL_DIAGNOSTICO = f"https://docs.google.com/spreadsheets/d/{ID_DA_PLANILHA}/gviz/tq?tqx=out:csv&sheet={nome_aba_codificado}"

def carregar_dados():
    df = pd.read_csv(URL_DIAGNOSTICO)
    coluna_data = df.columns[0]
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    return df

# Função auxiliar para classificar os níveis de risco e suas cores
def obter_classificacao_risco(media):
    if media <= 1.99:
        return "Risco Irrelevante", "#2E7D32", "🟢" # Verde Escuro
    elif 2.0 <= media <= 2.99:
        return "Risco Baixo", "#4CAF50", "🟢"      # Verde Claro
    elif 3.0 <= media <= 3.99:
        return "Risco Médio", "#FF9800", "🟡"      # Laranja
    elif 4.0 <= media <= 4.5:
        return "Risco Alto", "#E53935", "🔴"       # Vermelho
    else:
        return "Risco Crítico", "#8B0000", "🚨"     # Vermelho Escuro

try:
    df_completo = carregar_dados()
    col_data = df_completo.columns[0]
    col_cnpj = df_completo.columns[1]
    
    # Lógica de Captura do CNPJ via URL
    params = st.query_params
    cnpj_via_url = params.get("cnpj", None)

    if cnpj_via_url:
        df_original = df_completo[df_completo[col_cnpj].astype(str).str.strip() == str(cnpj_via_url).strip()]
        if df_original.empty:
            st.warning(f"⚠️ O CNPJ '{cnpj_via_url}' não foi encontrado. Exibindo dados gerais.")
            df_original = df_completo
        else:
            st.success(f"🏢 Empresa/CNPJ Selecionado: {cnpj_via_url}")
    else:
        df_original = df_completo
        st.info("📊 Visão geral de todas as empresas.")

    # Isolar colunas de perguntas (3ª à 43ª)
    colunas_perguntas = list(df_original.columns[2:43])
    for col in colunas_perguntas:
        df_original[col] = pd.to_numeric(df_original[col], errors='coerce')
        
    df_perguntas = df_original[colunas_perguntas]
    media_geral = df_perguntas.mean().mean()

    # --- ALTERAÇÃO 2 e 3: Visão Geral e Termômetro de Risco Centralizado ---
    st.markdown("---")
    st.subheader("📌 Visão Geral dos Riscos")
    
    # Criando o grande destaque centralizado para o nível de risco
    nome_risco, cor_risco, emoji_risco = obter_classificacao_risco(media_geral)
    
    col_vazia1, col_central, col_vazia2 = st.columns([1, 2, 1])
    with col_central:
        st.markdown(
            f"""
            <div style="background-color: {cor_risco}; padding: 25px; border-radius: 15px; text-align: center; color: white; box-shadow: 2px 4px 10px rgba(0,0,0,0.15);">
                <h3 style="margin: 0; font-size: 20px; text-transform: uppercase; letter-spacing: 1px; color: rgba(255,255,255,0.85);">Classificação Geral Atual</h3>
                <h1 style="margin: 10px 0; font-size: 45px; font-weight: bold;">{emoji_risco} {nome_risco}</h1>
                <p style="margin: 0; font-size: 22px; font-weight: 500; color: rgba(255,255,255,0.9);">Média do Diagnóstico: {media_geral:.2f} / 5.00</p>
            </div>
            """, 
            unsafe_allow_html=True
        )

    # --- ALTERAÇÃO 7: Quadro de Datas do Início e Fim da Pesquisa ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.metric(label="Total de Questionários", value=len(df_original))
    
    if not df_original[col_data].isna().all():
        data_inicio = df_original[col_data].min().strftime('%d/%m/%Y')
        data_fim = df_original[col_data].max().strftime('%d/%m/%Y')
        col_d2.metric(label="📅 Início da Pesquisa", value=data_inicio)
        col_d3.metric(label="📅 Término da Pesquisa", value=data_fim)
    else:
        col_d2.metric(label="📅 Início da Pesquisa", value="Sem dados")
        col_d3.metric(label="📅 Término da Pesquisa", value="Sem dados")

    st.markdown("---")

    # --- ALTERAÇÃO 4: Gráfico Distribuição de Todas as Respostas Formatado ---
    st.subheader("📊 Distribuição de Todas as Respostas por Nível de Risco")
    
    # Mapeando rigorosamente cada resposta individual dada na planilha (valores de 1 a 5)
    contagem_respostas = df_perguntas.melt()['value'].dropna()
    
    contagem_niveis = {
        "Risco Irrelevante (1)": len(contagem_respostas[contagem_respostas == 1]),
        "Risco Baixo (2)": len(contagem_respostas[contagem_respostas == 2]),
        "Risco Médio (3)": len(contagem_respostas[contagem_respostas == 3]),
        "Risco Alto (4)": len(contagem_respostas[contagem_respostas == 4]),
        "Risco Crítico (5)": len(contagem_respostas[contagem_respostas == 5])
    }
    
    df_dist_novo = pd.DataFrame(list(contagem_niveis.items()), columns=['Nível de Risco', 'Quantidade de Respostas'])
    st.bar_chart(data=df_dist_novo, x='Nível de Risco', y='Quantidade de Respostas', color="#4B70DD")

    st.markdown("---")

    # --- ALTERAÇÃO 5: 8 Gráficos Pequenos por Dimensões Lado a Lado ---
    st.subheader("🔲 Análise Detalhada por Dimensões Ocupacionais")
    
    dimensoes = {
        "Demandas de Trabalho": colunas_perguntas[0:5],
        "Controle sobre o Trabalho": colunas_perguntas[5:10],
        "Suporte Social no Trabalho": colunas_perguntas[10:15],
        "Relações Interpessoais e Liderança": colunas_perguntas[15:20],
        "Reconhecimento e Recompensas": colunas_perguntas[20:25],
        "Danos Morais e Assedio": colunas_perguntas[25:30],
        "Equilibrio Trabalho - Vida Pessoal": colunas_perguntas[30:35],
        "Insegurança no Trabalho": colunas_perguntas[35:40]
    }
    
    # Criando grid estruturado: 4 colunas em cima, 4 colunas embaixo
    chaves_dim = list(dimensoes.keys())
    
    # Linha 1 (Dimensões 1 a 4)
    cols_linha1 = st.columns(4)
    for idx in range(4):
        nome_dim = chaves_dim[idx]
        cols_dim = dimensoes[nome_dim]
        df_sub = df_perguntas[cols_dim]
        media_dim = df_sub.mean().mean()
        
        r_nome, r_cor, r_emoji = obter_classificacao_risco(media_dim)
        
        with cols_linha1[idx]:
            st.markdown(f"##### {nome_dim}")
            st.markdown(f"<span style='color:{r_cor}; font-weight:bold;'>{r_emoji} {r_nome} ({media_dim:.2f})</span>", unsafe_allow_html=True)
            
            # Montar mini gráfico de barras para as perguntas daquela dimensão
            df_mini = df_sub.mean().reset_index()
            df_mini.columns = ['Item', 'Média']
            st.bar_chart(data=df_mini, x='Item', y='Média', color=r_cor)
            st.markdown("<br>", unsafe_allow_html=True)

    # Linha 2 (Dimensões 5 a 8)
    cols_linha2 = st.columns(4)
    for idx in range(4, 8):
        nome_dim = chaves_dim[idx]
        cols_dim = dimensoes[nome_dim]
        df_sub = df_perguntas[cols_dim]
        media_dim = df_sub.mean().mean()
        
        r_nome, r_cor, r_emoji = obter_classificacao_risco(media_dim)
        
        with cols_linha2[idx - 4]:
            st.markdown(f"##### {nome_dim}")
            st.markdown(f"<span style='color:{r_cor}; font-weight:bold;'>{r_emoji} {r_nome} ({media_dim:.2f})</span>", unsafe_allow_html=True)
            
            df_mini = df_sub.mean().reset_index()
            df_mini.columns = ['Item', 'Média']
            st.bar_chart(data=df_mini, x='Item', y='Média', color=r_cor)
            st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")

    # --- ALTERAÇÃO 6: Exibição Condicional de Textos/Planos de Ação ---
    if "Baixo" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Baixo")
        st.info("👉 [Substitua este texto pelo seu Plano de Ação para Risco Baixo futuramente...]")
        
    elif "Médio" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Médio")
        st.warning("👉 [Substitua este texto pelo seu Plano de Ação para Risco Médio futuramente...]")
        
    elif "Alto" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Alto")
        st.error("👉 [Substitua este texto pelo seu Plano de Ação para Risco Alto futuramente...]")

except Exception as e:
    st.error(f"Erro ao processar o diagnóstico: {e}")
   
 
