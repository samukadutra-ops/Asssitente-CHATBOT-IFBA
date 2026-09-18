import streamlit as st
import google.generativeai as genai
import PyPDF2
import glob

# Configuração visual da página
st.set_page_config(page_title="Assistente IFBA", page_icon="🎓")
st.title("Assistente Virtual - IFBA 🎓")
st.write("Olá! Sou o assistente virtual do IFBA (Campus Brumado). Faça a sua pergunta e consultarei os nossos regulamentos e PPCs para lhe responder.")

# Conectar a chave da API
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Erro: Chave da API não encontrada nos Secrets do Streamlit.")

# Função rápida para ler todos os PDFs da pasta
@st.cache_data(show_spinner="A ler regulamentos do IFBA, por favor aguarde...")
def carregar_conhecimento():
    texto = ""
    # Procura todos os ficheiros PDF na pasta
    documentos = [
        "REGULAMENTO DISCENTE.pdf",
        "Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.pdf"
    ]
    for doc in documentos:
        texto += f"\n\n--- DOCUMENTO: {doc} ---\n\n"
        try:
            leitor = PyPDF2.PdfReader(doc)
            for pagina in leitor.pages:
                if pagina.extract_text():
                    texto += pagina.extract_text() + "\n"
        except Exception as e:
            pass
    return texto

# Iniciar a extração dos documentos para a base de dados do bot
base_de_dados = carregar_conhecimento()

# Configurar o modelo do Google
model = genai.GenerativeModel('gemini-3-flash-preview')

# Memória da conversa
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Caixa de texto para o estudante
if prompt := st.chat_input("Ex: Qual é a carga horária de Informática?"):
    # Mostra a pergunta do estudante
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Enviar a pergunta junto com os PDFs para o Gemini
    with st.chat_message("assistant"):
        mensagem_escondida = f"""
        És o Assistente Académico oficial do IFBA Campus Brumado. 
        Responde APENAS com base nos documentos abaixo. 
        Se a resposta não estiver nos documentos, informa educadamente que não tens essa informação e orienta o estudante a procurar a secretaria ou a coordenação.
        Sê claro, objetivo e utiliza um tom institucional.

        DOCUMENTOS INSTITUCIONAIS:
        {base_de_dados}

        PERGUNTA DO ESTUDANTE:
        {prompt}
        """
        
        # Gera e mostra a resposta baseada nos PDFs
        resposta = model.generate_content(mensagem_escondida)
        st.markdown(resposta.text)
        
    # Guarda a resposta na memória
    st.session_state.messages.append({"role": "assistant", "content": resposta.text})
