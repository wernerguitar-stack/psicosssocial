# -*- coding: utf-8 -*-
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
    
    # FORÇAR FORMATO DE DATA BRASILEIRO NO DATAFRAME COMPLETO
    if col_data in df_completo.columns:
        df_completo[col_data] = pd.to_datetime(df_completo[col_data], errors='coerce')
    
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
        
    # Cálculos das Médias Gerais e por Pergunta
    media_geral = df_perguntas.mean().mean()
    
    # Calcula a média individual de cada uma das 40 perguntas
    medias_por_pergunta = df_perguntas.mean()
    menor_media_resposta = medias_por_pergunta.min()
    maior_media_resposta = medias_por_pergunta.max()

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

    # --- Quadro de Informações Principais ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.metric(label="Total de Questionários", value=len(df_original))
    
    if not df_original[col_data].isna().all():
        # Formata o início e fim da pesquisa explicitamente no formato brasileiro
        data_inicio = df_original[col_data].min().strftime('%d/%m/%Y')
        data_fim = df_original[col_data].max().strftime('%d/%m/%Y')
        col_d2.metric(label="📅 Início da Pesquisa", value=data_inicio)
        col_d3.metric(label="📅 Término da Pesquisa", value=data_fim)
    else:
        col_d2.metric(label="📅 Início da Pesquisa", value="Sem dados")
        col_d3.metric(label="📅 Término da Pesquisa", value="Sem dados")

    # --- Nova Linha de Cartões: Menor e Maior Média ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_inf1, col_inf2 = st.columns(2)
    
    # Descobre os emojis de classificação para as extremidades
    _, _, emoji_menor = obter_classificacao_risco(menor_media_resposta)
    _, _, emoji_maior = obter_classificacao_risco(maior_media_resposta)
    
    col_inf1.metric(
        label="📉 Menor Média Encontrada (Item de Menor Risco)", 
        value=f"{emoji_menor} {menor_media_resposta:.2f} / 5.00"
    )
    col_inf2.metric(
        label="📈 Maior Média Encontrada (Item Crítico / Maior Risco)", 
        value=f"{emoji_maior} {maior_media_resposta:.2f} / 5.00"
    )

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
    st.markdown("---")

    # =========================================================================
    # INSERÇÃO DO TEXTO METODOLÓGICO LONGO
    # =========================================================================
    st.subheader("📝 Fundamentação e Metodologia do Diagnóstico")
    
    st.markdown("""
    Quanto à identificação dos fatores psicossociais relacionados ao trabalho, utilizamos a metodologia baseada na ferramenta internacionalmente reconhecida **Copenhagen Psychosocial Questionnaire (COPSOQ II)**, em versão adaptada de 40 itens, aplicada por meio de plataforma digital especializada, para coleta de informações junto aos trabalhadores.

    #### ⚖️ Fundamentação Legal
    A **Portaria MTE nº 1.419/2024** atualizou o Capítulo 1.5 da **NR-01**, incluindo os *Fatores Psicossociais Relacionados ao Trabalho (FRPRT)* no processo de gestão de riscos, em conformidade com a **NR-17**. Os trechos a seguir destacam essa exigência:
    * **Item 1.5.3.1.4:** *"O gerenciamento de riscos deve abranger agentes físicos, químicos, biológicos, riscos de acidentes e fatores ergonômicos, incluindo os fatores psicossociais."*
    * **Item 1.5.3.2.1:** *"As condições de trabalho, nos termos da NR-17, devem incluir os fatores psicossociais."*
    * **Item 1.5.4.4.5.3:** *"A avaliação de riscos ergonômicos, incluindo psicossociais, deve considerar as exigências da atividade e a eficácia das medidas de prevenção."*

    #### 🔬 Metodologia de Identificação
    O método aplicado tem como objetivo identificar possíveis situações estressoras no ambiente de trabalho, por meio da coleta estruturada de informações junto à empresa, aos trabalhadores e de visitas de campo. 
    
    O **COPSOQ II** é um instrumento multidimensional com consenso internacional quanto à sua validade, abrangência e aplicabilidade na avaliação de riscos psicossociais em contexto laboral. A versão adaptada utilizada nesta metodologia contempla 40 itens, derivados da versão curta do COPSOQ II, organizados em múltiplas dimensões que abrangem:
    1. Demandas de Trabalho
    2. Controle sobre o Trabalho
    3. Suporte Social no Trabalho
    4. Relações Interpessoais e Liderança
    5. Reconhecimento e Recompensas
    6. Danos Morais e Assedio
    7. Equilibrio Trabalho
    8. Insegurança no Trabalho
    
    *Todos os itens are avaliados em escala Likert de 5 pontos.*

    #### 📊 Critérios de Interpretação dos Resultados
    O instrumento segue uma escala de resposta estruturada in níveis de frequência, variando de **1 a 5**, onde:
    * **1** representa *"Nunca"*
    * **2** representa *"Raramente"*
    * **3** representa *"Às vezes"*
    * **4** representa *"Frequentemente"*
    * **5** representa *"Sempre"*

    Essa metodologia permite quantificar percepções subjetivas de forma padronizada, possibilitando análise comparativa entre indivíduos, equipes e dimensões organizacionais. A tabulação é realizada por meio do cálculo de médias aritméticas simples, tanto no nível geral quanto por dimensões específicas do ambiente de trabalho.
    
    A classificação de risco é derivada da média obtida, sendo categorizada em níveis progressivos de criticidade:
    """)

    # Tabela Visual dos Critérios
    st.markdown("""
    | Média Obtida | Classificação de Risco | Nível de Criticidade |
    | :--- | :--- | :--- |
    | 🟢 **≤ 1.99** | **IRRELEVANTE** | Exposição insignificante a estressores |
    | 🟢 **2.00 a 2.99** | **BAIXO** | Situação sob controle e estável |
    | 🟡 **3.00 a 3.99** | **MÉDIO** | Alerta; requer atenção a médio prazo |
    | 🔴 **4.00 a 4.50** | **ALTO** | Crítico; exige intervenção programada |
    | 🚨 **> 4.50** | **CRÍTICO** | Extremo; exige ação imediata de contenção |
    """)

    st.markdown("""
    #### 👥 Procedimento de Aplicação e Amostragem
    O questionário é aplicado ao conjunto de funcionários da organização, **sem identificação de setor ou função**. Essa opção metodológica fundamenta-se em três razões de ordem prática e ética:
    * **Preservação efetiva do anonimato:** Em setores com reduzido número de colaboradores, a associação entre cargo e resposta tornaria inevitável a identificação do respondente, comprometendo a integridade ética do processo.
    * **Fidedignidade dos dados coletados:** O preenchimento de informações ocupacionais é fonte recorrente de erros sistemáticos, como classificação incorreta de setor ou função, que comprometem a qualidade da tabulação.
    * **Conformidade normativa:** A NR-01 não determina a segmentação por setor como requisito obrigatório para a avaliação dos fatores psicossociais, sendo a avaliação institucional do perfil de risco igualmente válida para fins de gestão e composição do PGR.

    > ⚠️ **Adesão Mínima:** Deverá ser alcançado um índice mínimo de **70% de adesão** do quadro total de funcionários para que os resultados sejam considerados representativos. Caso esse percentual não seja atingido, recomenda-se nova rodada de aplicação. As respostas são estritamente anônimas e confidenciais.

    #### 📂 Análise e Inserção no PGR
    Após a fase de coleta, o profissional deverá utilizar os relatórios gerados pela plataforma de aplicação do COPSOQ II para identificar a presença e o nível de exposição aos fatores de risco psicossociais. Na sequência, será realizado o anexo dos resultados dos fatores de risco ergonômicos psicossociais diretamente no **PGR (Programa de Gerenciamento de Riscos)**.

    #### 📅 Vigência
    A metodologia de avaliação será implementada em acompanhamento à atualização da nova redação da NR-01, que entrará em vigor em **26 de maio de 2026**.
    
    ---
    *ID de Controle Emissor: SSOCIAL MEDCURITIBA-V2026*
    """)
    st.markdown("<br>", unsafe_allow_html=True)
    # =========================================================================

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

7. **Equilíbrio Trabalho–Vida Pessoal** (Rotina, pausas e qualidade de vida)  
- Treinamentos sobre gestão do tempo, quality de vida, saúde mental e limites saudáveis no ambiente de trabalho.

8. **Insegurança no Trabalho** (Incertezas, estabilidade e mudanças organizacionais)  
- Treinamentos sobre adaptação a mudanças organizacionais e comunicação corporativa.
""")

    elif "Médio" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Médio")
        st.info("""
1. **Demandas de Trabalho** (Carga de trabalho, prazos, volume e urgências)  
- Treinamentos específicos sobre gestão de demandas, organização operacional, priorização de atividades e prevenção do estresse relacionado ao trabalho.

2. **Controle sobre o Trabalho** (Autonomia, participação e organização das atividades)  
- Treinamentos específicos sobre autonomia, clareza de função, organização operacional e melhoria dos processos internos.

3. **Suporte Social no Trabalho** (Apoio entre equipes, cooperação e integração)  
- Treinamentos voltados à comunicação interna, cooperação entre equipes e fortalecimento do suporte social no ambiente de trabalho.

4. **Relações Interpessoais e Liderança** (Comunicação, feedback e gestão de conflitos)  
- Treinamentos específicos para liderança e equipes sobre feedback, alinhamento de comunicação, prevenção de conflitos e fortalecimento das relações profissionais.

5. **Reconhecimento e Recompensas** (Valorização profissional e percepção de reconhecimento)  
- Treinamentos direcionados às lideranças sobre práticas de reconhecimento, valorização profissional e retenção de talentos.

6. **Danos Morais e Assédio** (Condutas inadequadas, constrangimentos e ambiente ético)  
- Treinamentos específicos sobre políticas internas, prevenção ao assédio, comunicação ética e fortalecimento das boas práticas organizacionais.

7. **Equilíbrio Trabalho–Vida Pessoal** (Rotina, pausas e qualidade de vida)  
- Treinamentos educativos sobre equilíbrio ocupacional, prevenção do desgaste emocional e incentivo a práticas saudáveis relacionadas ao bem-estar.

8. **Insegurança no Trabalho** (Incertezas, estabilidade e mudanças organizacionais)  
- Treinamentos voltados à transparência organizacional, alinhamento de expectativas profissionais e fortalecimento da comunicação interna.
""")

    elif "Alto" in nome_risco:
        st.subheader("📋 Plano de Ação Sugerido - Grau de Risco Alto")
        st.info("""
1. **Demandas de Trabalho** (Carga de trabalho, prazos, volume e urgências)  
- Necessidade de acompanhamento mais próximo e estruturado, com mentoria presencial para liderança, reorganização operacional, redistribuição de demandas e desenvolvimento de estratégias práticas de redução do risco psicossocial.

2. **Controle sobre o Trabalho** (Autonomia, participação e organização das atividades)  
- Necessidade de mentoria presencial para liderança e reestruturação organizacional, visando fortalecimento da autonomia funcional, alinhamento de funções e melhoria dos processos internos.

3. **Suporte Social no Trabalho** (Apoio entre equipes, cooperação e integração)  
- Necessidade de workshops e mentoria presencial voltados à melhoria da comunicação interpessoal, fortalecimento da cultura colaborativa e desenvolvimento das equipes.

4. **Relações Interpessoais e Liderança** (Comunicação, feedback e gestão de conflitos)  
- Necessidade de mentoria presencial para liderança, gestão de conflitos, fortalecimento de engajamento e melhoria das relações interpessoais no ambiente organizacional.

5. **Reconhecimento e Recompensas** (Valorização profissional e percepção de reconhecimento)  
- Necessidade de mentoria presencial para implementação de estratégias de reconhecimento, fortalecimento da motivação organizacional e retenção de talentos.

6. **Danos Morais e Assédio** (Condutas inadequadas, constrangimentos e ambiente ético)  
- Necessidade de palestras, acompanhamento presencial, fortalecimento de canais internos e mentoria especializada para prevenção e manejo das situações identificadas.

7. **Equilíbrio Trabalho–Vida Pessoal** (Rotina, pausas e qualidade de vida)  
- Necessidade de workshops presenciais, acompanhamento especializado e mentoria voltada ao manejo emocional, prevenção do adoecimento ocupacional e fortalecimento do bem-estar no ambiente de trabalho.

8. **Insegurança no Trabalho** (Incertezas, estabilidade e mudanças organizacionais)  
- Necessidade de mentoria presencial para liderança, alinhamento organizacional, fortalecimento da segurança psicológica e acompanhamento estruturado das mudanças organizacionais.
""")

except Exception as e:
    st.error(f"Erro ao processar o diagnóstico: {e}")
