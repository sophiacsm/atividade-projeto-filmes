from dotenv import load_dotenv
load_dotenv(dotenv_path=r'C:\Users\Yuri\Documents\atividade-projeto-filmes\.env')
import os
import json
import re
import streamlit as st
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from google import genai

# Carrega as chaves
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Inicializa modelos
groq_model = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, api_key=GROQ_API_KEY)
client = genai.Client(api_key=GEMINI_KEY)

# Pasta para armazenar históricos
HISTORY_DIR = "chats"
os.makedirs(HISTORY_DIR, exist_ok=True)

def salvar_historico(nome_chat, mensagens, titulo=None):
    data = {
        "title": titulo or nome_chat,
        "messages": mensagens
    }
    with open(f"{HISTORY_DIR}/{nome_chat}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def carregar_historico(nome_chat):
    try:
        with open(f"{HISTORY_DIR}/{nome_chat}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("messages", []), data.get("title", nome_chat)
    except FileNotFoundError:
        return [], nome_chat
    
def gerar_titulo_resumo(mensagens):
    prompt = "Resuma este diálogo em no máximo 6 palavras para servir como título de um chat:"
    texto = prompt + "\n\n" + "\n".join([f"{m['role']}: {m['content']}" for m in mensagens[:4]])
    response = client.models.generate_content(model='gemini-2.0-flash', contents=texto)
    return response.text.strip().replace("\n", " ")[:60]

def listar_chats_com_titulos():
    chats = []
    for filename in os.listdir(HISTORY_DIR):
        if filename.endswith(".json"):
            nome = filename.replace(".json", "")
            try:
                with open(os.path.join(HISTORY_DIR, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    titulo = data.get("title", nome)
                    chats.append((nome, titulo))
            except:
                chats.append((nome, nome))
    return chats

def listar_chats():
    return [f.replace(".json", "") for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]

def is_python_request(text):
    padroes = [
        r"código em python", r"script python", r"como faço.*em python",
        r"exemplo.*python", r"me dê.*python", r"escreva.*python",
        r"gere.*python", r"código em Python"
    ]
    return any(re.search(p, text.lower()) for p in padroes)

# Inicializa sessão
if "chat_nome" not in st.session_state:
    st.session_state.chat_nome = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar: seleção de chat e novo chat
with st.sidebar:
    st.subheader("💬 Meus Chats")

    chats_info = listar_chats_com_titulos()
    opcoes_sidebar = [""] + [f"{t} ({n})" for n, t in chats_info]
    escolha = st.selectbox("Chats salvos", opcoes_sidebar)

    if escolha:
        nome_real = escolha.split("(")[-1].replace(")", "")
        if nome_real != st.session_state.chat_nome:
            st.session_state.chat_nome = nome_real
            st.session_state.messages, _ = carregar_historico(nome_real)
            st.rerun()

    if st.button("➕ Novo Chat"):
        novo_nome = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.chat_nome = novo_nome
        st.session_state.messages = []
        st.rerun()

# Título
st.title("🤖 Chat com Groq + Gemini")
st.caption(f"Chat atual: `{st.session_state.chat_nome}`")
st.write("💡 Peça por códigos Python para ativar o Gemini.")

# Exibe o histórico
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada do usuário
user_input = st.chat_input("Digite sua mensagem")

if user_input:
    # Exibe pergunta
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Decide modelo
    if is_python_request(user_input):
        gemini_response = client.models.generate_content(model='gemini-2.0-flash', contents=user_input)
        response = gemini_response.text
    else:
        response_obj = groq_model.invoke([HumanMessage(content=user_input)])
        response = response_obj.content

    # Mostra resposta
    st.chat_message("assistant").markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

        # Salva chat
    if st.session_state.chat_nome.startswith("chat_"):  # Ainda sem título
        titulo = gerar_titulo_resumo(st.session_state.messages)
    else:
        titulo = None

    salvar_historico(st.session_state.chat_nome, st.session_state.messages, titulo)