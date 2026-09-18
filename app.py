import streamlit as st
import google.generativeai as genai
import glob

# Configuração visual
st.set_page_config(page_title="Assistente IFBA", page_icon="🎓")
st.title("Assistente Virtual - IFBA 🎓")

st.write("Olá! Sou o assistente virtual do IFBA (Campus Brumado). Faça a sua pergunta!")

st.warning("""
**Aviso Importante:** Sou uma ferramenta de inteligência artificial em fase de teste. 
Apesar de consultar a base de conhecimento (PPCs, normas e regulamentos), possuo limitações e posso cometer erros de interpretação. 
**As minhas respostas não substituem a leitura dos documentos oficiais nem as orientações dos servidores e setores do IFBA-Campus Brumado.**
""")
# Conectar a chave
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Função para enviar os PDFs e Textos (.txt) para a nuvem da Google
@st.cache_resource(show_spinner="A memorizar todos os documentos oficiais do IFBA. Isto demora um pouco na primeira vez...")
def preparar_documentos():
    arquivos_locais = glob.glob("*.pdf") + glob.glob("*.txt")
    arquivos_prontos = []
    
    # Verifica o que já foi enviado para a nuvem para não duplicar
    arquivos_na_nuvem = {f.display_name: f for f in genai.list_files()}
    
    for caminho in arquivos_locais:
        if caminho in arquivos_na_nuvem:
            arquivo = arquivos_na_nuvem[caminho]
        else:
            arquivo = genai.upload_file(path=caminho, display_name=caminho)
            
        # O sistema espera até o arquivo estar totalmente processado
        while arquivo.state.name == "PROCESSING":
            time.sleep(2)
            arquivo = genai.get_file(arquivo.name)
            
        # SÓ ADICIONA O DOCUMENTO SE A LEITURA FOI UM SUCESSO
        if arquivo.state.name == "ACTIVE":
            arquivos_prontos.append(arquivo)
        else:
            # Se o PDF estiver corrompido, ele avisa na tela e ignora
            st.error(f"Atenção: O ficheiro '{caminho}' está corrompido ou tem um formato ilegível e foi ignorado.")
            
    return arquivos_prontos

# Iniciar o processamento dos ficheiros
documentos_base = preparar_documentos()

# Configurar o modelo 
model = genai.GenerativeModel('gemini-3-flash-preview')

# Memória do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ex: Qual é a carga horária de Informática?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        instrucao = "És o Assistente Académico oficial do IFBA Campus Brumado. Responde APENAS com base nos documentos em anexo. Se não souberes a resposta, orienta o aluno a contactar a coordenação."
        
        # Junta a instrução, TODOS os ficheiros PDF em anexo e a pergunta do utilizador
        conteudo_completo = [instrucao] + documentos_base + [prompt]
        
        resposta = model.generate_content(conteudo_completo)
        st.markdown(resposta.text)
        
    st.session_state.messages.append({"role": "assistant", "content": resposta.text})
