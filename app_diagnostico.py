import streamlit as st
import pandas as pd
import urllib.parse

# 1. Configuração da página do site
st.set_page_config(page_title="Análise de Diagnóstico de Risco", layout="wide")
st.title("📊 Relatório Avançado: Diagnóstico de Risco (1 a 5)")

# =========================================================================
# 🔴 ATENÇÃO: SUBSTITUA O ID ABAIXO PELO ID REAL DA SUA PLANILHA GOOGLE
ID_DA_PLANILHA = "1klYEryQRKGUjTN7XOHf9fqprRQTqcYUcEIu0TIfQtc4"
NOME_DA_ABA = "PLANILHA TÉCNICO" 
# =========================================================================

# Codificação do nome da aba para evitar erros de acentos na URL (como o erro de ASCII)
nome_aba_codificado = urllib.parse.quote(NOME_DA_ABA)
URL_DIAGNOSTICO = f"https://docs.google.com/spreadsheets/d/{ID_DA_PLANILHA}/gviz/tq?tqx=out:csv&sheet={nome_aba_codificado}"

def carregar_dados():
    # Faz o download dos dados em tempo real do Google Sheets
    df = pd.read_csv(URL_DIAGNOSTICO)
    
    # Converte a primeira coluna para o formato de Data do Python
    coluna_data = df.columns[0]
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
    return df

try:
    df_completo = carregar_dados()
    col_cnpj = df_completo.columns[1] # Segunda coluna da planilha é o CNPJ
    
    # ---------------------------------------------------------------------
    # LÓGICA DA URL: Captura o CNPJ que o seu outro site enviou pelo link
    # ---------------------------------------------------------------------
    params = st.query_params
    cnpj_via_url = params.get("cnpj", None)

    if cnpj_via_url:
        # Se veio um CNPJ na URL, filtra a planilha para isolar APENAS os dados dele
        df_original = df_completo[df_completo[col_cnpj].astype(str).str.strip() == str(cnpj_via_url).strip()]
        
        if df_original.empty:
            st.warning(f"⚠️ O CNPJ '{cnpj_via_url}' foi enviado pelo site, mas não foi encontrado nesta planilha.")
            df_original = df_completo # Mostra tudo para não quebrar a tela se houver erro de digitação
        else:
            st.success(f"🏢 Exibindo indicadores exclusivos para o CNPJ: {cnpj_via_url}")
    else:
        # Se o link for aberto direto sem passar CNPJ, exibe a média geral de todas as empresas
        df_original = df_completo
        st.info("📊 Exibindo a visão geral de todas as empresas (Nenhum CNPJ foi informado na URL).")
    # ---------------------------------------------------------------------

    # Identificar colunas de perguntas (da 3ª até a 43ª coluna)
    colunas_perguntas = list(df_original.columns[2:43])
    
    # Garante que todas as respostas das perguntas sejam lidas como números de 1 a 5
    for col in colunas_perguntas:
        df_original[col] = pd.to_numeric(df_original[col], errors='coerce')
        
    df_perguntas = df_original[colunas_perguntas]

    # --- CÁLCULOS MATEMÁTICOS DOS INDICADORES ---
    media_geral = df_perguntas.mean().mean()
    
    # Conta a quantidade de notas 1, 2, 3, 4 e 5 dadas no questionário
    contagem_notas = df_perguntas.melt()['value'].value_counts().sort_index()
    
    # Mapeia os números para os nomes dos riscos correspondentes
    nomes_risco = {1.0: "Irrelevante (1)", 2.0: "Baixo (2)", 3.0: "Médio (3)", 4.0: "Alto (4)", 5.0: "Crítico (5)"}
    df_distribuicao = pd.DataFrame({'Quantidade': contagem_notas})
    df_distribuicao['Nível de Risco'] = df_distribuicao.index.map(nomes_risco)

    # --- EXIBIÇÃO DOS COMPONENTES VISUAIS NA TELA ---
    
    # Bloco 1: Cartões de Métrica (KPIs)
    st.subheader("📌 Panorama Geral de Maturidade")
    col1, col2, col3 = st.columns(3)
    
    col1.metric(label="Total de Diagnósticos Avaliados", value=len(df_original))
    
    cor_alerta = "normal" if media_geral < 3 else "inverse"
    col2.metric(label="Média Geral de Risco", value=f"{media_geral:.2f} / 5.00", delta="Alvo: < 2.0", delta_color=cor_alerta)
    
    total_respostas = contagem_notas.sum()
    respostas_criticas = contagem_notas.get(4.0, 0) + contagem_notas.get(5.0, 0)
    pct_critico = (respostas_criticas / total_respostas) * 100 if total_respostas > 0 else 0
    col3.metric(label="Percentual de Riscos Altos/Críticos", value=f"{pct_critico:.1f}%")

    st.markdown("---")

    # Bloco 2: Gráficos de Barras e Linhas
    col_esq, col_dir = st.columns(2)
    
    with col_esq:
        st.subheader("📊 Distribuição de Todas as Respostas")
        st.bar_chart(data=df_distribuicao, x='Nível de Risco', y='Quantidade', color="#FF4B4B")
        
    with col_dir:
        st.subheader("📈 Evolução do Risco Médio ao Longo do Tempo")
        col_data = df_original.columns[0]
        if not df_original[col_data].isna().all():
            df_temporal = df_original.copy()
            df_temporal['Mês/Ano'] = df_temporal[col_data].dt.to_period('M').astype(str)
            df_mes = df_temporal.groupby('Mês/Ano')[colunas_perguntas].mean().mean(axis=1).reset_index()
            df_mes.columns = ['Mês/Ano', 'Risco Médio']
            st.line_chart(data=df_mes, x='Mês/Ano', y='Risco Médio')
        else:
            st.info("Insira datas válidas na primeira coluna para ver o gráfico de evolução temporal.")

    st.markdown("---")

    # Bloco 3: Painel de Gargalos (Rankings)
    st.subheader("🔍 Detalhes por Pergunta: Maiores Problemas e Acertos")
    col_ranking_ruim, col_ranking_bom = st.columns(2)
    
    medias_por_pergunta = df_perguntas.mean().sort_values(ascending=False).reset_index()
    medias_por_pergunta.columns = ['Pergunta / Item Avaliado', 'Média de Risco']
    
    with col_ranking_ruim:
        st.error("🚨 Top 5 Itens Mais Críticos (Maior Risco - Perto de 5)")
        st.dataframe(medias_por_pergunta.head(5), use_container_width=True, hide_index=True)
        
    with col_ranking_bom:
        st.success("✅ Top 5 Itens Mais Seguros (Menor Risco - Perto de 1)")
        st.dataframe(medias_por_pergunta.tail(5).iloc[::-1], use_container_width=True, hide_index=True)

    st.markdown("---")

    # Bloco 4: Tabela com as respostas abertas do filtro aplicado
    st.subheader("📋 Dados Brutos Avaliados")
    st.dataframe(df_original, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar o diagnóstico: {e}")
    st.info("Dica técnica: Lembre-se de configurar a sua planilha no Google Sheets para que 'Qualquer pessoa com o link possa ler'.")