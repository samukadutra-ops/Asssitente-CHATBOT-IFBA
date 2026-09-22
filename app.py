import streamlit as st
import google.generativeai as genai
import glob
import time

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
    arquivos_prontos = {}
    
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
            arquivos_prontos[caminho] = arquivo
        else:
            st.error(f"Atenção: O ficheiro '{caminho}' está corrompido ou tem um formato ilegível e foi ignorado.")
            
    return arquivos_prontos

# Iniciar o processamento dos ficheiros
documentos_disponiveis = preparar_documentos()

# Configurar o modelo (Usando o 1.5-flash para resolver a Falha 429 de excesso de requisições)
model = genai.GenerativeModel('gemini-1.5-flash')

# Histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ==============================================================================
# MEMÓRIA DE CURTO PRAZO
# ==============================================================================
if "esperando_curso" not in st.session_state:
    st.session_state.esperando_curso = False
if "pergunta_pendente" not in st.session_state:
    st.session_state.pergunta_pendente = ""

# ==============================================================================
# INTERAÇÃO DO CHAT E ROTEAMENTO INFALÍVEL
# ==============================================================================
if prompt := st.chat_input("Ex: Como funciona a recuperação? Quebrei uma cadeira, o que acontece?"):
    
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
    # REGRAS DE TRIAGEM COM RADICAIS
    # ==========================================================================
    
    # REGRA 1: Recuperação, Avaliação e Pareceres do MEC
    tags_recuperacao = ["recuper", "reavali", "nota", "ldb", "parecer", "cne", "ceb", "800 horas", "200 dias", "supletiv", "reprov", "baixo rendimento", "prova"]
    if any(tag in p_lower for tag in tags_recuperacao):
        arquivos_alvo.append("Nota sobre estudos de recuperação.txt")
        arquivos_alvo.append("Parecer CNE nº 12-1997.txt")
        arquivos_alvo.append("Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.txt")

    # REGRA 2: Calendário e Datas
    tags_calendario = ["data", "feriad", "unidad", "calend", "recess", "aula", "iníci", "inici", "términ", "termin", "prazo", "féri", "feri", "sábad", "sabad", "reunião", "reuniao", "formatura"]
    if any(tag in p_lower for tag in tags_calendario):
        arquivos_alvo.append("Calendário Acadêmico técnico integrado ensino médio informática edificações.txt")

    # REGRA 3: Regulamento Discente (Comportamento, Convivência e Punições)
    tags_comportamento = ["advert", "agred", "agress", "bebid", "bebeu", "alcool", "álcool", "arma", "faca", "assed", "asséd", "bully", "comportament", "condut", "dano", "depred", "desacat", "desrespeit", "dever", "direit", "disciplin", "droga", "maconha", "fum", "cigarro", "fard", "uniform", "fraud", "colar", "colou", "plagi", "infrac", "infraç", "puni", "quebr", "estrag", "responsabilidad", "suspens", "tca", "trote", "vandalism", "brig", "xing", "ofend", "ofens", "roub", "furt", "namor", "beij", "sexo", "mau uso", "cadeira", "carteira", "mesa", "patrimônio"]
    if any(tag in p_lower for tag in tags_comportamento):
        arquivos_alvo.append("REGULAMENTO DISCENTE.txt")

    # REGRA 4: Normas Acadêmicas do Ensino Superior
    tags_superior = ["superior", "graduaç", "graduac", "bacharel", "licenciatura", "tecnólog", "tecnolog", "enade", "jubil", "crédit", "credit", "coeficiente", "cre", "cap", "exame final", "revalid", "pré-req", "pre-req", "choque", "ouvinte", "especial"]
    if any(tag in p_lower for tag in tags_superior):
        arquivos_alvo.append("Normas Academicas do Ensino Superior do IFBA - RESOLUCAO_N._23_DE_2019_.txt")
        if "REGULAMENTO DISCENTE.txt" not in arquivos_alvo:
            arquivos_alvo.append("REGULAMENTO DISCENTE.txt")

    # REGRA 5: Normas Acadêmicas Gerais (Médio/Técnico)
    tags_normas = ["falt", "tranc", "destranc", "norma", "regulament", "atestad", "justific", "transfer", "dependênc", "dependenc", "avaliac", "avaliaç", "média", "media", "reintegr", "rendimento", "domiciliar", "eja", "fic", "integrad", "subsequent", "concomitant", "chamada", "renova", "turno", "matutin", "vespertin", "noturn"]
    if any(tag in p_lower for tag in tags_normas):
        if not any(ts in p_lower for ts in ["superior", "graduaç", "graduac", "bacharel"]):
            arquivos_alvo.append("Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.txt")

    # REGRA 6: Projetos Pedagógicos de Curso (PPCs)
    tags_ppc = ["estág", "estag", "tcc", "monografia", "carga hor", "matriz", "currícul", "curricul", "acex", "extens", "complementar", "acc", "barema", "ppa", "integraliza", "egress", "diplom", "certific", "colegiado", "nde", "núcleo", "nucleo", "disciplin"]
    if any(tag in p_lower for tag in tags_ppc):
        curso_identificado = False
        
        if "informática" in p_lower or "informatica" in p_lower:
            arquivos_alvo.append("PPC Informática - forma INTEGRADA.pdf")
            curso_identificado = True
            
        if "edificações" in p_lower or "edificacoes" in p_lower:
            arquivos_alvo.append("PPC Edificações - forma INTEGRADA.pdf")
            curso_identificado = True
            
        if "minas" in p_lower or "mineração" in p_lower or "mineracao" in p_lower or "engenharia" in p_lower:
            arquivos_alvo.append("PPC_Engenharia_de_Minas__2023_.pdf")
            curso_identificado = True
            
        # Trava: se falou de PPC mas não disse o curso, pergunta na tela
        if not curso_identificado:
            precisa_perguntar_curso = True
            arquivos_alvo = []

    # ==========================================================================
    # SALVAGUARDA ABSOLUTA (Prioridade em caso de dúvida genérica)
    # ==========================================================================
    if len(arquivos_alvo) == 0 and not precisa_perguntar_curso:
        arquivos_alvo = [
            "Normas_Academicas_atualizada_Resolucao_154__de_12_de_dezembro_de_2024.txt",
            "REGULAMENTO DISCENTE.txt",
            "Nota sobre estudos de recuperação.txt",
            "Parecer CNE nº 12-1997.txt"
        ]

    # Remove arquivos duplicados
    arquivos_alvo = list(set(arquivos_alvo))

    # ==========================================================================
    # EXECUÇÃO: ENVIO PARA A INTELIGÊNCIA ARTIFICIAL
    # ==========================================================================
    with st.chat_message("assistant"):
        
        if precisa_perguntar_curso:
            st.session_state.esperando_curso = True
            st.session_state.pergunta_pendente = pergunta_completa
            resposta_curso = "Para consultar a matriz, carga horária ou diretrizes corretas, preciso saber: **Qual é o seu curso e nível?** (Ex: Informática Integrado, Edificações Integrado, Engenharia de Minas...)"
            st.markdown(resposta_curso)
            st.session_state.messages.append({"role": "assistant", "content": resposta_curso})
            
        else:
            with st.spinner("A consultar os regulamentos institucionais pertinentes..."):
                try:
                    conteudo_para_gemini = []
                    
                    for nome_arquivo in arquivos_alvo:
                        doc_obj = documentos_disponiveis.get(nome_arquivo)
                        if doc_obj:
                            conteudo_para_gemini.append(doc_obj)
                        else:
                            st.warning(f"O documento '{nome_arquivo}' não foi encontrado no servidor. Verifique os nomes no GitHub.")
                    
                    if conteudo_para_gemini:
                        prompt_sistema = f"""Você é o assistente virtual oficial do IFBA Campus Brumado. Sua missão é responder à dúvida do aluno de forma clara, educada e embasada nos documentos anexados. 
JAMAIS se negue a responder se o assunto constar nos textos. Se a resposta exigir interpretação de múltiplas regras (ex: recuperação, avaliação), cruze as informações dos documentos (como o Parecer do MEC e as Normas Acadêmicas) e ofereça a melhor orientação institucional possível, citando os setores responsáveis quando necessário.

Dúvida do aluno: {pergunta_completa}"""
                        
                        conteudo_para_gemini.append(prompt_sistema)
                        
                        resposta = model.generate_content(conteudo_para_gemini)
                        st.markdown(resposta.text)
                        st.session_state.messages.append({"role": "assistant", "content": resposta.text})
                        
                except Exception as e:
                    if "ResourceExhausted" in str(e):
                        st.warning("O sistema atingiu o limite gratuito de acessos por minuto. Por favor, aguarde 60 segundos e pergunte novamente.")
                    else:
                        st.error(f"Ocorreu uma falha técnica durante a consulta: {e}")
