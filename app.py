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
# ==============================================================================
# 🧠 MEMÓRIA DE CURTO PRAZO (Evita gastar tokens com perguntas incompletas)
# ==============================================================================
if "esperando_curso" not in st.session_state:
    st.session_state.esperando_curso = False
if "pergunta_pendente" not in st.session_state:
    st.session_state.pergunta_pendente = ""

# ==============================================================================
# 🤖 INTERAÇÃO DO CHAT E ROTEAMENTO INTELIGENTE (O "Poupador de Tokens")
# ==============================================================================
if prompt := st.chat_input("Ex: Quando começam as aulas? ou Como funciona o estágio de Informática?"):
    
    # Exibe a pergunta do aluno na tela
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Verifica se a IA estava à espera da resposta sobre qual é o curso
    if st.session_state.esperando_curso:
        pergunta_completa = f"O aluno perguntou anteriormente: '{st.session_state.pergunta_pendente}'. Agora ele complementou informando o curso: '{prompt}'."
        st.session_state.esperando_curso = False
        st.session_state.pergunta_pendente = ""
    else:
        pergunta_completa = prompt

    p_lower = pergunta_completa.lower()
    arquivos_alvo = []
    precisa_perguntar_curso = False

    # ==========================================================================
    # 🎯 REGRAS DE TRIAGEM COM TAGS MAXIMIZADAS
    # ==========================================================================
    
    # REGRA 1: Calendário e Datas
    tags_calendario = ["data", "feriado", "unidade", "calendário", "calendario", "recesso", "aula", "início", "término", "prazo", "férias", "ferias", "sábado letivo", "sabado letivo", "dia letivo", "conselho de classe", "reunião de pais", "formatura", "snct", "jogos interclasse", "quando"]
    if any(tag in p_lower for tag in tags_calendario):
        arquivos_alvo.append("Calendário Acadêmico técnico integrado ensino médio informática edificações.txt")

    # REGRA 2: Normas do Ensino Superior
    tags_superior = ["superior", "graduação", "graduacao", "faculdade", "bacharelado", "licenciatura", "enade", "jubilamento", "tcc superior"]
    if any(tag in p_lower for tag in tags_superior):
        arquivos_alvo.append("Normas Academicas do Ensino Superior do IFBA - RESOLUCAO_N._23_DE_2019_.txt")
        arquivos_alvo.append("REGULAMENTO DISCENTE.txt")

    # REGRA 3: Normas Gerais, Discentes e Matrícula (Ensino Médio/Técnico Padrão)
    tags_normas = ["matrícula", "matricula", "falta", "trancamento", "norma", "regulamento", "atestado", "justificativa", "transferência", "transferencia", "dependência", "dependencia", "direitos", "deveres", "punição", "advertência", "avaliação", "nota", "média", "media", "frequência", "frequencia", "reintegração", "rendimento"]
    if any(tag in p_lower for tag in tags_normas):
        arquivos_alvo.append("REGULAMENTO DISCENTE.txt")
        # Se não for especificamente superior, puxa as normas do médio por padrão
        if "superior" not in p_lower and "graduação" not in p_lower:
            arquivos_alvo.append("Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.txt")

    # REGRA 4: Recuperação e Parecer CNE
    tags_recuperacao = ["recuperação", "recuperacao", "prova final", "exame final", "parecer", "cne"]
    if any(tag in p_lower for tag in tags_recuperacao):
        arquivos_alvo.append("Nota sobre estudos de recuperação.txt")
        arquivos_alvo.append("Parecer CNE nº 12-1997.txt")
        if "REGULAMENTO DISCENTE.txt" not in arquivos_alvo:
            arquivos_alvo.append("REGULAMENTO DISCENTE.txt")

    # REGRA 5: Estágio, Matrizes Curriculares e PPCs (Exige saber o curso!)
    tags_ppc = ["estágio", "estagio", "matriz", "carga horária", "carga horaria", "disciplina", "ppc", "curso", "ementa", "pré-requisito", "pre-requisito", "horas complementares", "atividades complementares", "perfil do egresso", "laboratório"]
    if any(tag in p_lower for tag in tags_ppc):
        
        # Tenta identificar qual é o curso na pergunta
        curso_identificado = False
        
        if "informática" in p_lower or "informatica" in p_lower:
            arquivos_alvo.append("PPC Informática - forma INTEGRADA.pdf")
            curso_identificado = True
            
        if "edificações" in p_lower or "edificacoes" in p_lower:
            arquivos_alvo.append("PPC Edificações - forma INTEGRADA.pdf")
            curso_identificado = True
            
        if "minas" in p_lower or "mineração" in p_lower or "mineracao" in p_lower:
            arquivos_alvo.append("PPC_Engenharia_de_Minas__2023_.pdf")
            curso_identificado = True
            
        # Se ele perguntou sobre algo da matriz/estágio, mas NÃO disse o curso:
        if not curso_identificado:
            precisa_perguntar_curso = True
            # Limpa os arquivos alvo para não enviar nada para a IA ainda
            arquivos_alvo = []

    # ==========================================================================
    # 🚀 EXECUÇÃO: ENVIO PARA A INTELIGÊNCIA ARTIFICIAL
    # ==========================================================================
    with st.chat_message("assistant"):
        
        # CASO 1: O aluno perguntou sobre disciplinas, mas esqueceu de dizer o curso.
        if precisa_perguntar_curso:
            st.session_state.esperando_curso = True
            st.session_state.pergunta_pendente = pergunta_completa
            resposta_curso = "Para que eu possa consultar as normas de estágio, disciplinas ou carga horária corretas, preciso saber: **Qual é o seu curso e o nível?** (Ex: Informática Integrado, Edificações Integrado, Engenharia de Minas...)"
            st.markdown(resposta_curso)
            st.session_state.messages.append({"role": "assistant", "content": resposta_curso})
            
        # CASO 2: A pergunta não bateu com nenhuma tag. Aciona o aviso institucional.
        elif len(arquivos_alvo) == 0:
            resposta_padrao = "No momento, não identifiquei essa informação na minha base de regulamentos oficiais (Calendários, PPCs e Normas Acadêmicas). Para orientações específicas, por favor, contate a **Secretaria de Registros Acadêmicos**, a **Coordenação do seu Curso** ou a **Coordenação Pedagógica** do Campus Brumado."
            st.markdown(resposta_padrao)
            st.session_state.messages.append({"role": "assistant", "content": resposta_padrao})

        # CASO 3: Tudo perfeito! Pega APENAS os arquivos selecionados e faz a leitura.
        else:
            # Remove arquivos duplicados da lista, caso alguma regra tenha sobreposto
            arquivos_alvo = list(set(arquivos_alvo))
            
            with st.spinner("Consultando os regulamentos institucionais pertinentes..."):
                try:
                    conteudo_para_gemini = []
                    
                    for nome_arquivo in arquivos_alvo:
                        doc_obj = documentos_disponiveis.get(nome_arquivo)
                        if doc_obj:
                            conteudo_para_gemini.append(doc_obj)
                        else:
                            st.warning(f"O documento '{nome_arquivo}' não foi encontrado na nuvem. Verifique o GitHub.")
                    
                    # Se encontrou os arquivos, junta com o prompt e envia!
                    if conteudo_para_gemini:
                        prompt_sistema = f"Você é o assistente virtual do IFBA Campus Brumado. Responda à dúvida do aluno de forma clara, educada e direta, baseando-se ESTRITAMENTE nos documentos em anexo.\n\nDúvida do aluno: {pergunta_completa}"
                        conteudo_para_gemini.append(prompt_sistema)
                        
                        resposta = model.generate_content(conteudo_para_gemini)
                        st.markdown(resposta.text)
                        st.session_state.messages.append({"role": "assistant", "content": resposta.text})
                        
                except Exception as e:
                    if "ResourceExhausted" in str(e):
                        st.warning("O sistema está recebendo muitas requisições simultâneas. Por favor, aguarde cerca de 1 minuto e faça sua pergunta novamente.")
                    else:
                        st.error("Ocorreu uma instabilidade na conexão com a base de dados. Tente novamente.")
