import streamlit as st
import google.generativeai as genai
import glob
import os

# Configuração visual e descrição focada em normas acadêmicas e disciplinares
st.set_page_config(page_title="Assistente de Normas - IFBA", page_icon="🎓")
st.title("Assistente Virtual de Normas Acadêmicas e Disciplinares - IFBA 🎓")

st.write("Olá! Sou o assistente virtual do IFBA (Campus Brumado), especializado exclusivamente em orientações sobre **normas acadêmicas e disciplinares**. Faça a sua pergunta!")

st.warning("""
**Aviso Importante:** Sou uma ferramenta de inteligência artificial em fase de teste. 
Consulte a base de conhecimento oficial (Normas Acadêmicas do Ensino Médio/Superior, Regulamento Discente e Nota de Recuperação). 
**As minhas respostas não substituem a leitura dos documentos oficiais nem as orientações dos servidores e setores do IFBA-Campus Brumado.**
""")

# Conectar a chave da API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Função para carregar todo o texto dos arquivos .txt locais de forma leve
@st.cache_resource(show_spinner="A carregar os regulamentos locais...")
def carregar_bases_locais():
    bases = {}
    arquivos = glob.glob("*.txt")
    for arq in arquivos:
        try:
            with open(arq, "r", encoding="utf-8") as f:
                bases[arq] = f.read()
        except Exception as e:
            try:
                with open(arq, "r", encoding="latin-1") as f:
                    bases[arq] = f.read()
            except Exception as ex:
                st.error(f"Erro ao ler o arquivo {arq}: {ex}")
    return bases

documentos_texto = carregar_bases_locais()

# Configuração do modelo Gemini 3 Flash Preview do Google AI Studio
model = genai.GenerativeModel('gemini-3-flash-preview')

# Histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 🤖 INTERAÇÃO DO CHAT E ROTEAMENTO POR PALAVRAS-CHAVE LOCAL
# ==============================================================================
if prompt := st.chat_input("Ex: Como funciona a recuperação? O que acontece se quebrar uma cadeira?"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    p_lower = prompt.lower()
    textos_selecionados = ""

    # ==========================================================================
    # 🎯 SELEÇÃO INTELIGENTE DE TEXTO BASEADA NOS FICHEIROS .TXT LOCAIS
    # ==========================================================================
    
    # 1. Recuperação e Avaliação -> Direciona para a Nota de Recuperação
    tags_recuperacao = ["recuper", "reavali", "baixo rendimento", "estudos paralelos", "paralela", "contínua", "continua", "frequência", "frequencia"]
    if any(tag in p_lower for tag in tags_recuperacao):
        if "Nota sobre estudos de recuperação.txt" in documentos_texto:
            textos_selecionados += "\n\n--- NOTA SOBRE ESTUDOS DE RECUPERAÇÃO ---\n" + documentos_texto["Nota sobre estudos de recuperação.txt"]

    # 2. Comportamento e Disciplina -> Direciona para o Regulamento Discente
    tags_discente = [
        "advert", "agred", "agress", "bebid", "alcool", "álcool", "arma", "assed", "asséd", 
        "bully", "comportament", "condut", "dano", "depred", "desacat", "desrespeit", "dever", 
        "direit", "disciplin", "droga", "fum", "cigarro", "fard", "uniform", "fraud", "colar", 
        "colou", "plagi", "infrac", "infraç", "puni", "quebr", "estrag", "responsabilidad", 
        "suspens", "tca", "trote", "vandalism", "brig", "xing", "ofend", "ofens", "roub", "furt", 
        "namor", "beij", "cadeira", "patrimôni", "patrimoni", "mau uso"
    ]
    if any(tag in p_lower for tag in tags_discente):
        if "REGULAMENTO DISCENTE.txt" in documentos_texto:
            textos_selecionados += "\n\n--- REGULAMENTO DISCENTE ---\n" + documentos_texto["REGULAMENTO DISCENTE.txt"]

    # 3. Ensino Superior -> Direciona para as Normas do Superior
    tags_superior = ["superior", "graduaç", "graduac", "bacharel", "licenciatura", "tecnólog", "tecnolog", "enade", "jubil", "crédit", "credit", "coeficiente", "cre", "cap", "exame final", "revalid", "ouvinte"]
    if any(tag in p_lower for tag in tags_superior):
        for nome_arq, conteudo in documentos_texto.items():
            if "superior" in nome_arq.lower():
                textos_selecionados += f"\n\n--- {nome_arq} ---\n" + conteudo

    # 4. Ensino Médio / Técnico -> Direciona para as Normas Acadêmicas do Médio
    tags_medio = [
        "matrícul", "matricul", "falt", "tranc", "destranc", "atestad", "justific", "transfer", 
        "dependênc", "dependenc", "avaliac", "avaliaç", "média", "media", "reintegr", "rendimento", 
        "domiciliar", "eja", "fic", "integrad", "subsequent", "concomitant", "chamada", "renova", 
        "turno", "matutin", "vespertin", "noturn", "conselho de classe", "conselho de curso", "estágio", "estagio"
    ]
    if any(tag in p_lower for tag in tags_medio):
        if not any(ts in p_lower for ts in ["superior", "graduaç", "graduac", "bacharel"]):
            for nome_arq, conteudo in documentos_texto.items():
                if "resolucao_154" in nome_arq.lower() or ("normas" in nome_arq.lower() and "superior" not in nome_arq.lower()):
                    textos_selecionados += f"\n\n--- {nome_arq} ---\n" + conteudo

    # ==========================================================================
    # 🛡️ SALVAGUARDA ABSOLUTA
    # ==========================================================================
    if len(textos_selecionados.strip()) == 0:
        for nome_arq, conteudo in documentos_texto.items():
            textos_selecionados += f"\n\n--- {nome_arq} ---\n" + conteudo

    # ==========================================================================
    # 🚀 EXECUÇÃO DA CONSULTA COM O GEMINI 3 FLASH PREVIEW
    # ==========================================================================
    with st.chat_message("assistant"):
        with st.spinner("A analisar os regulamentos..."):
            try:
                prompt_sistema = f"""Você é o assistente virtual oficial de normas acadêmicas e disciplinares do IFBA Campus Brumado. 
Responda à dúvida do utilizador com base estrita nos regulamentos fornecidos abaixo. 
JAMAIS se negue a responder se o assunto constar nos textos. Se a pergunta do utilizador for muito vaga, incompleta ou genérica (por exemplo, apenas uma palavra sem contexto), responda com base nos regulamentos e oriente o utilizador a fornecer mais detalhes (como o curso ou a situação específica).

REGULAMENTOS DE REFERÊNCIA:
{textos_selecionados}

Dúvida do utilizador: {prompt}"""
                
                resposta = model.generate_content(prompt_sistema)
                st.markdown(resposta.text)
                st.session_state.messages.append({"role": "assistant", "content": resposta.text})
                
            except Exception as e:
                if "ResourceExhausted" in str(e):
                    st.warning("O sistema atingiu o limite de consultas por minuto da API. Aguarde um instante e tente novamente.")
                else:
                    st.error(f"Ocorreu um erro técnico: {e}")
