import streamlit as st
import google.generativeai as genai

# Configuração da página da web
st.set_page_config(page_title="Assistente IFBA", page_icon="📚")
st.title("Assistente Virtual - IFBA 🎓")
st.write("Olá! Sou o assistente virtual do IFBA. Faça a sua pergunta sobre os nossos regulamentos académicos.")

# Ligar a sua chave da API (esta chave ficará escondida num cofre mais à frente)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.warning("A chave da API será configurada no próximo passo.")

# Inicializar o cérebro do robô
model = genai.GenerativeModel('gemini-1.5-flash')

# Criar a memória da conversa
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar as mensagens anteriores no ecrã
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Caixa de texto para o aluno escrever
if prompt := st.chat_input("Escreva a sua dúvida aqui..."):
    # Guardar e mostrar o que o aluno escreveu
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Processar a resposta com o Gemini
    with st.chat_message("assistant"):
        # NOTA: Numa próxima fase, vamos injetar o texto dos PDFs aqui!
        resposta = model.generate_content(prompt)
        st.markdown(resposta.text)
        
    # Guardar a resposta da IA na memória
    st.session_state.messages.append({"role": "assistant", "content": resposta.text})
