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

# ==============================================================================
# MEMÓRIA DE CURTO PRAZO PARA PERGUNTAS INCOMPLETAS
# ==============================================================================
if "esperando_curso" not in st.session_state:
    st.session_state.esperando_curso = False
if "pergunta_pendente" not in st.session_state:
    st.session_state.pergunta_pendente = ""

# ==============================================================================
# INTERAÇÃO DO CHAT E ROTEAMENTO INTELIGENTE
# ==============================================================================
if prompt := st.chat_input("Digite a sua dúvida sobre o IFBA Campus Brumado..."):
    
    # Exibe a mensagem do usuário na tela
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Verifica se estávamos à espera que o aluno dissesse o curso
    if st.session_state.esperando_curso:
        # Junta a pergunta anterior com o curso que ele acabou de digitar
        pergunta_completa = f"{st.session_state.pergunta_pendente}. (Curso especificado pelo aluno: {prompt})"
        st.session_state.esperando_curso = False
        st.session_state.pergunta_pendente = ""
    else:
        pergunta_completa = prompt

    p_lower = pergunta_completa.lower()
    arquivos_alvo = []
    precisa_perguntar_curso = False

    # ==========================================================================
    # REGRAS DE TRIAGEM (Adicione os nomes EXATOS dos seus arquivos aqui)
    # ==========================================================================
    
    # REGRA 1: Datas, Feriados e Calendário -> Vai APENAS no Calendário
    if any(tag in p_lower for tag in ["data", "feriado", "unidade", "calendário", "calendario", "recesso", "aula"]):
        arquivos_alvo.append("calendario_integrado_2026.txt")

    # REGRA 2: Matrícula Médio Integrado -> Vai nas Normas e no Calendário
    if "matrícula" in p_lower or "matricula" in p_lower:
        arquivos_alvo.append("normas_academicas.txt")
        if "integrado" in p_lower and "calendario_integrado_2026.txt" not in arquivos_alvo:
            arquivos_alvo.append("calendario_integrado_2026.txt")

    # REGRA 3: Estágio, Matriz, Disciplinas -> Precisa do PPC e das Normas
    if any(tag in p_lower for tag in ["estágio", "estagio", "matriz", "carga horária", "disciplina", "ppc"]):
        if "normas_academicas.txt" not in arquivos_alvo:
            arquivos_alvo.append("normas_academicas.txt")
        
        # Tenta identificar o curso na pergunta
        if "informática" in p_lower or "informatica" in p_lower:
            arquivos_alvo.append("ppc_informatica.pdf")
        elif "edificações" in p_lower or "edificacoes" in p_lower:
            arquivos_alvo.append("ppc_edificacoes.pdf")
        elif "mineração" in p_lower or "mineracao" in p_lower:
            arquivos_alvo.append("ppc_mineracao.pdf")
        else:
            # Se não encontrar nenhum curso na frase, liga o alerta para perguntar
            precisa_perguntar_curso = True

    # ==========================================================================
    # EXECUÇÃO DAS REGRAS
    # ==========================================================================
    with st.chat_message("assistant"):
        
        # AÇÃO A: O aluno não disse o curso. O bot pergunta e NÃO gasta tokens.
        if precisa_perguntar_curso:
            st.session_state.esperando_curso = True
            st.session_state.pergunta_pendente = pergunta_completa
            resposta_curso = "Para consultar a matriz, o estágio ou a carga horária correta, preciso saber: **Qual é o seu curso e nível?** (Ex: Informática Integrado, Edificações Subsequente, etc.)"
            st.markdown(resposta_curso)
            st.session_state.messages.append({"role": "assistant", "content": resposta_curso})
            
        # AÇÃO B: Assunto não identificado. Informa o balcão de atendimento.
        elif len(arquivos_alvo) == 0:
            resposta_padrao = "No momento, não disponho desta informação na minha base de regulamentos. Para orientações específicas sobre este assunto, por favor, contacte a **Secretaria de Registos Acadêmicos** ou a **Coordenação do seu Curso** no campus."
            st.markdown(resposta_padrao)
            st.session_state.messages.append({"role": "assistant", "content": resposta_padrao})

        # AÇÃO C: Tudo certo! Envia apenas os arquivos filtrados para o Gemini.
        else:
            with st.spinner(f"Consultando os arquivos: {', '.join(arquivos_alvo)}..."):
                try:
                    conteudo_para_gemini = []
                    
                    # Puxa da memória apenas os arquivos que a triagem escolheu
                    for nome_arquivo in arquivos_alvo:
                        doc_obj = documentos_disponiveis.get(nome_arquivo)
                        if doc_obj:
                            conteudo_para_gemini.append(doc_obj)
                        else:
                            st.warning(f"O arquivo {nome_arquivo} não foi encontrado na base.")
                    
                    # Junta os arquivos com a pergunta do aluno
                    conteudo_para_gemini.append(f"Responda estritamente com base nos documentos fornecidos:\n\n{pergunta_completa}")
                    
                    # Chama a inteligência artificial
                    resposta = model.generate_content(conteudo_para_gemini)
                    st.markdown(resposta.text)
                    st.session_state.messages.append({"role": "assistant", "content": resposta.text})
                    
                except Exception as e:
                    if "ResourceExhausted" in str(e):
                        st.warning("O sistema está com muitos acessos simultâneos. Por favor, aguarde cerca de 1 minuto e tente novamente.")
                    else:
                        st.error(f"Ocorreu um erro técnico: {e}")
