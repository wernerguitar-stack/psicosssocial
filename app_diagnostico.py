import streamlit as st
import pandas as pd
import urllib.parse
import requests
import re

# 1. Configuração da página do site
st.set_page_config(page_title="Dashboard NR-01", layout="wide")

# --- Nome do Painel ---
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
    df.columns = [col.strip() for col in df.columns]
    return df

# Busca o Nome da Empresa na ReceitaWS usando o CNPJ limpo
def buscar_nome_empresa(cnpj_limpo):
    try:
        url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
        resposta = requests.get(url, timeout=8)
        if resposta.status_code == 200:
            dados_cnpj = resposta.json()
            if dados_cnpj.get("status") == "OK":
                return dados_cnpj.get("nome")
    except Exception:
        pass
    return None

# Classificação dos níveis de risco e suas cores
def obter_classificacao_risco(media):
    if media <= 1.99:
        return "Risco Irrelevante", "#2E7D32", "🟢"
    elif 2.0 <= media <= 2.99:
        return "Risco Baixo", "#4CAF50", "🟢"
    elif 3.0 <= media <= 3.99:
        return "Risco Médio", "#FF9800", "🟡"
    elif 4.0 <= media <= 4.5:
        return "Risco Alto", "#E53935", "🔴"
    else:
        return "Risco Crítico", "#8B0000", "🚨"

try:
    df_completo = carregar_dados()
    col_data = df_completo.columns[0]
    col_cnpj = df_completo.columns[1] # Segunda coluna da planilha
    
    # Lógica de Captura do CNPJ via URL
    params = st.query_params
    cnpj_via_url = params.get("cnpj", None)

    if cnpj_via_url:
        # 1. Limpa o CNPJ da URL (deixa só números)
        cnpj_url_limpo = "".join(filter(str.isdigit, str(cnpj_via_url)))
        
        # 2. Cria uma coluna temporária na planilha com os CNPJs limpos (só números) para comparar
        df_completo['cnpj_limpo_temp'] = df_completo[col_cnpj].astype(str).str.replace(r'\D', '', regex=True)
        
        # 3. Faz a filtragem exata baseada apenas em números
        df_original = df_completo[df_completo['cnpj_limpo_temp'] == cnpj_url_limpo].copy()
        
        if df_original.empty:
            st.warning(f"⚠️ O CNPJ '{cnpj_via_url}' não foi encontrado na base de dados. Exibindo Visão Geral.")
            df_original = df_completo.copy()
        else:
            # Reseta o índice para isolar totalmente as linhas dessa empresa
            df_original = df_original.reset_index(drop=True)
            
            # Chama a API da Receita Federal usando o CNPJ limpo
            nome_empresa = buscar_nome_empresa(cnpj_url_limpo)
            if nome_empresa:
                st.success(f"🏢 Empresa Selecionada: **{nome_empresa}** ({cnpj_via_url})")
            else:
                st.success(f"🏢 Empresa/CNPJ Selecionado: {cnpj_via_url}")
    else:
        df_original = df_completo.copy()
        st.info("📊 Visão geral de todas as empresas.")

    # Isolar colunas de perguntas (3ª à 42ª coluna da tabela filtrada)
    colunas_perguntas = list(df_original.columns[2:42]) 
    df_perguntas = df_original[colunas_perguntas].copy()
    
    for col in colunas_perguntas:
        df_perguntas[col] = pd.to_numeric(df_perguntas[col], errors='coerce')
        
    media_geral = df_perguntas.mean().mean()

    # --- Visão Geral e Termômetro de Risco Centralizado ---
    st.markdown("---")
    st.subheader("📌 Visão Geral dos Riscos")
    
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

    # --- Quadro de Datas do Início e Fim da Pesquisa ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.metric(label="Total de Questionários", value=len(df_original))
    
    if not df_original[col_data].isna().all():
        data_inicio = pd.to_datetime(df_original[col_data], errors='coerce').min().strftime('%d/%m/%Y')
        data_fim = pd.to_datetime(df_original[col_data], errors='coerce').max().strftime('%d/%m/%Y')
        col_d2.metric(label="📅 Início da Pesquisa", value=data_inicio)
        col_d3.metric(label="📅 Término da Pesquisa", value=data_fim)
    else:
        col_d2.metric(label="📅 Início da Pesquisa", value="Sem dados")
        col_d3.metric(label="📅 Término da Pesquisa", value="Sem dados")

    st.markdown("---")

    # --- NOVO GRÁFICO: DISTRIBUIÇÃO POR QUESTIONÁRIOS (LINHAS) ---
    st.subheader("📊 Quantidade de Funcionários por Nível de Risco")
    
    # Calcula a média horizontal de cada linha (cada funcionário individualmente)
    medias_por_funcionario = df_perguntas.mean(axis=1)
    
    contagem_funcionarios = {
        "Risco Irrelevante (<=1.99)": int((medias_por_funcionario <= 1.99).sum()),
        "Risco Baixo (2.0 a 2.99)": int(((medias_por_funcionario >= 2.0) & (medias_por_funcionario <= 2.99)).sum()),
        "Risco Médio (3.0 a 3.99)": int(((medias_por_funcionario >= 3.0) & (medias_por_funcionario <= 3.99)).sum()),
        "Risco Alto (4.0 a 4.5)": int(((medias_por_funcionario >= 4.0) & (medias_por_funcionario <= 4.5)).sum()),
        "Risco Crítico (>4.5)": int((medias_por_funcionario > 4.5).sum())
    }
    
    df_dist_linhas = pd.DataFrame(list(contagem_funcionarios.items()), columns=['Nível de Risco', 'Quantidade de Funcionários'])
    st.bar_chart(data=df_dist_linhas, x='Nível de Risco', y='Quantidade de Funcionários', color="#4B70DD")

    st.markdown("---")

    # --- 8 Gráficos Pequenos por Dimensões Lado a Lado ---
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

    # --- Exibição Condicional de Textos/Planos de Ação ---
    if "Baixo" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Baixo")
        st.info("""
1. **Demandas de Trabalho** (Carga de trabalho, prazos, volume e urgências)  
- Treinamentos voltados à gestão do tempo, organização de tarefas, produtividade saudável e prevenção de sobrecarga ocupacional.

2. **Controle sobre o Trabalho** (Autonomia, participação e organização das atividades)  
- Treinamentos voltados à autogestão, autonomia funcional e organização da rotina de trabalho.

3. **Suporte Social no Trabalho** (Apoio entre equipes, cooperação e integração)  
- Treinamentos sobre relações interpessoais, integração e fortalecimento do trabalho em equipe.

4. **Relações Interpessoais e Liderança** (Comunicação, feedback e gestão de conflitos)  
- Treinamentos sobre comunicação assertiva, inteligência emocional e relacionamento interpessoal.

5. **Reconhecimento e Recompensas** (Valorização profissional e percepção de reconhecimento)  
- Treinamentos sobre cultura organizacional, reconhecimento profissional e valorização das equipes.

6. **Danos Morais e Assédio** (Condutas inadequadas, constrangimentos e ambiente ético)  
- Treinamentos sobre ética, respeito interpessoal e prevenção ao assédio moral e sexual.

7. **Equilíbrio Trabalho–Vida Pessoal** (Rotina, pausas e quality de vida)  
- Treinamentos sobre gestão do tempo, qualidade de vida, saúde mental e limites saudáveis no ambiente de trabalho.

8. **Insegurança no Trabalho** (Incertezas, estabilidade e mudanças organizacionais)  
- Treinamentos sobre adaptação a mudanças organizacionais e comunicação corporativa.
""")

    elif "Médio" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Médio")
        st.warning("👉 [Substitua este texto pelo seu Plano de Ação para Risco Médio futuramente...]")

    elif "Alto" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Alto")
        st.error("👉 [Substitua este texto pelo seu Plano de Ação para Risco Alto futuramente...]")

except Exception as e:
    st.error(f"Erro ao processar o diagnóstico: {e}")
