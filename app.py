import streamlit as st
import google.generativeai as genai
import glob
import time

# Configuração visual e nova descrição do chatbot
st.set_page_config(page_title="Assistente de Normas - IFBA", page_icon="🎓")
st.title("Assistente Virtual de Normas Acadêmicas e Disciplinares - IFBA 🎓")

st.write("Olá! Sou o assistente virtual do IFBA (Campus Brumado), especializado exclusivamente em orientações sobre **normas acadêmicas e disciplinares**. Faça a sua pergunta!")

st.warning("""
**Aviso Importante:** Sou uma ferramenta de inteligência artificial em fase de teste. 
Consulte a base de conhecimento oficial (Normas Acadêmicas do Ensino Médio/Superior, Regulamento Discente e Nota de Recuperação). 
**As minhas respostas não substituem a leitura dos documentos oficiais nem as orientações dos servidores e setores do IFBA-Campus Brumado.**
""")

# Conectar a chave
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Função para carregar os ficheiros `.txt` exatos da nuvem
@st.cache_resource(show_spinner="A memorizar os documentos oficiais de normas e disciplina...")
def preparar_documentos():
    arquivos_locais = glob.glob("*.txt")
    arquivos_prontos = {}
    
    arquivos_na_nuvem = {f.display_name: f for f in genai.list_files()}
    
    for caminho in arquivos_locais:
        if caminho in arquivos_na_nuvem:
            arquivo = arquivos_na_nuvem[caminho]
        else:
            arquivo = genai.upload_file(path=caminho, display_name=caminho)
            
        while arquivo.state.name == "PROCESSING":
            time.sleep(2)
            arquivo = genai.get_file(arquivo.name)
            
        if arquivo.state.name == "ACTIVE":
            arquivos_prontos[caminho] = arquivo
        else:
            st.error(f"Atenção: O ficheiro '{caminho}' está corrompido ou ilegível.")
            
    return arquivos_prontos

documentos_disponiveis = preparar_documentos()

# Configuração do modelo do AI Studio
model = genai.GenerativeModel('gemini-3-flash-preview')

# Histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# 🤖 INTERAÇÃO DO CHAT E ROTEAMENTO INTELIGENTE POR FICHEIRO
# ==============================================================================
if prompt := st.chat_input("Ex: Como funciona a recuperação? Qual a regra para trancamento?"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    p_lower = prompt.lower()
    arquivos_alvo = []

    # ==========================================================================
    # 🎯 MAPEAMENTO DE PALAVRAS-CHAVE PARA OS FICHEIROS EXATOS
    # ==========================================================================
    
    # 1. RECUPERAÇÃO E AVALIAÇÃO -> "Nota sobre estudos de recuperação.txt"
    tags_recuperacao = [
        "recuper", "reavali", "baixo rendimento", "estudos paralelos", 
        "recuperação paralela", "recuperação contínua", "frequência de estudos"
    ]
    if any(tag in p_lower for tag in tags_recuperacao):
        arquivos_alvo.append("Nota sobre estudos de recuperação.txt")

    # 2. COMPORTAMENTO, DISCIPLINA E PUNIÇÕES -> "REGULAMENTO DISCENTE.txt"
    tags_discente = [
        "advert", "agred", "agress", "bebid", "alcool", "álcool", "arma", 
        "assed", "asséd", "bully", "comportament", "condut", "dano", "depred", 
        "desacat", "desrespeit", "dever", "direit", "disciplin", "droga", "fum", 
        "cigarro", "fard", "uniform", "fraud", "colar", "colou", "plagi", 
        "infrac", "infraç", "puni", "quebr", "estrag", "responsabilidad", 
        "suspens", "tca", "trote", "vandalism", "brig", "xing", "ofend", "ofens", 
        "roub", "furt", "namor", "beij", "cadeira", "patrimôni", "patrimoni"
    ]
    if any(tag in p_lower for tag in tags_discente):
        arquivos_alvo.append("REGULAMENTO DISCENTE.txt")

    # 3. ENSINO SUPERIOR (Graduação) -> "Normas Acadêmicas do Ensino Superior do IFBA..."
    tags_superior = [
        "superior", "graduaç", "graduac", "bacharel", "licenciatura", "tecnólog", 
        "tecnolog", "enade", "jubil", "crédit", "credit", "coeficiente", "cre", 
        "cap", "exame final", "revalid", "ouvinte", "estudante especial", "colegiado superior"
    ]
    if any(tag in p_lower for tag in tags_superior):
        arquivos_alvo.append("Normas Academicas do Ensino Superior do IFBA - RESOLUCAO_N._23_DE_2019_.txt")

    # 4. ENSINO MÉDIO / TÉCNICO -> "Normas_Academicas_atualizada_Resolucao_154..."
    tags_medio = [
        "matrícul", "matricul", "falt", "tranc", "destranc", "atestad", "justific", 
        "transfer", "dependênc", "dependenc", "avaliac", "avaliaç", "média", "media", 
        "reintegr", "rendimento", "domiciliar", "eja", "fic", "integrad", "subsequent", 
        "concomitant", "chamada", "renova", "turno", "matutin", "vespertin", "noturn", 
        "conselho de classe", "conselho de curso", "estágio", "estagio"
    ]
    if any(tag in p_lower for tag in tags_medio):
        if not any(ts in p_lower for ts in ["superior", "graduaç", "graduac", "bacharel"]):
            arquivos_alvo.append("Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.txt")

    # ==========================================================================
    # 🛡️ SALVAGUARDA ABSOLUTA (Se nenhuma tag exata bater, usa as normas gerais)
    # ==========================================================================
    if len(arquivos_alvo) == 0:
        arquivos_alvo = [
            "Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.txt",
            "REGULAMENTO DISCENTE.txt"
        ]

    arquivos_alvo = list(set(arquivos_alvo))

    # ==========================================================================
    # 🚀 EXECUÇÃO DA CONSULTA COM O GEMINI
    # ==========================================================================
    with st.chat_message("assistant"):
        with st.spinner("A consultar os documentos de normas institucionais..."):
            try:
                conteudo_para_gemini = []
                
                for nome_arquivo in arquivos_alvo:
                    doc_obj = documentos_disponiveis.get(nome_arquivo)
                    if doc_obj:
                        conteudo_para_gemini.append(doc_obj)
                
                if conteudo_para_gemini:
                    prompt_sistema = f"""Você é o assistente virtual oficial de normas acadêmicas e disciplinares do IFBA Campus Brumado. 
Responda à dúvida do utilizador com base estrita nos documentos normativos anexados. 
Se a pergunta for genérica ou incompleta, responda com base no regulamento e oriente o utilizador a fornecer mais detalhes (como o curso ou o procedimento específico). Nunca recuse responder se o tema constar nos textos.

Dúvida: {prompt}"""
                    
                    conteudo_para_gemini.append(prompt_sistema)
                    
                    resposta = model.generate_content(conteudo_para_gemini)
                    st.markdown(resposta.text)
                    st.session_state.messages.append({"role": "assistant", "content": resposta.text})
                    
            except Exception as e:
                if "ResourceExhausted" in str(e):
                    st.warning("O sistema atingiu o limite de consultas por minuto. Aguarde um instante e tente novamente.")
                else:
                    st.error(f"Ocorreu um erro técnico: {e}")
