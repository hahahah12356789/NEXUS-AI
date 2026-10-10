import os
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
import openai
from tavily import TavilyClient
import json

st.set_page_config(page_title="NEXUS 🌐 AI", page_icon="🌐", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    :root { --primary-color: #1E40AF; }
    .logo-container { text-align: center; margin-top: -30px; margin-bottom: 20px; }
    .welcome-text { text-align: center; color: #94A3B8; font-size: 20px; font-weight: 500; margin-top: 80px; margin-bottom: 40px; }
    .stChatMessage[data-testid="stChatMessageUser"] { background-color: #EBF4FF; border-radius: 15px; border-left: 4px solid #1E40AF; margin-top: 10px; }
    .stChatMessage[data-testid="stChatMessageAssistant"] { background-color: #F8FAFC; border-radius: 15px; border-left: 4px solid #10B981; margin-top: 10px; }
    .disclaimer { font-size: 12px !important; color: #94A3B8 !important; margin-top: 8px !important; margin-bottom: 4px !important; border-top: 1px solid #E2E8F0 !important; padding-top: 6px !important; display: inline-block !important; }
    .stButton>button { background-color: #1E40AF !important; color: white !important; border-radius: 8px; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #1E3A8A !important; }
    div[data-testid="stChatInput"] { border: 1.5px solid #CBD5E1 !important; border-radius: 14px !important; background-color: #FFFFFF !important; box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important; transition: all 0.3s ease; margin-top: 20px; }
    div[data-testid="stChatInput"]:focus-within { border-color: #1E40AF !important; box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.2) !important; }
    div[data-testid="stChatInput"] textarea:focus { box-shadow: none !important; border: none !important; }
    div[data-testid="stChatInput"] button { background-color: #1E40AF !important; color: white !important; border-radius: 50% !important; width: 38px !important; height: 38px !important; padding: 0 !important; display: flex !important; align-items: center !important; justify-content: center !important; margin-right: 4px !important; border: none !important; transition: all 0.3s ease; }
    div[data-testid="stChatInput"] button:hover { background-color: #1E3A8A !important; transform: scale(1.05); }
    div[data-testid="stChatInput"] button svg { fill: white !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# 从云端 Secrets 读取密钥（如果是在本地测试，它会尝试从 config.json 读）
try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
    ACCESS_PASSWORD = st.secrets.get("ACCESS_PASSWORD", "") # 如果没有设置密码，默认空
except:
    # 本地测试时的兜底
    DEEPSEEK_API_KEY = ""
    TAVILY_API_KEY = ""
    ACCESS_PASSWORD = ""

# 如果本地没有配置 Secrets，才尝试读本地文件
if not DEEPSEEK_API_KEY and os.path.exists("config.json"):
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            local_config = json.load(f)
            DEEPSEEK_API_KEY = local_config.get("api_key", "")
            TAVILY_API_KEY = local_config.get("tavily_key", "")
    except: pass

st.markdown("""
<div class="logo-container">
    <svg width="70" height="70" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="45" fill="url(#bg)"/>
        <defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#1E40AF"/><stop offset="100%" stop-color="#1E3A8A"/></linearGradient></defs>
        <path d="M28 68 L28 32 L72 68 L72 32" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="50" cy="50" r="7" fill="#10B981"/>
    </svg>
    <h1 style="margin-top: 10px; color: #1E3A8A;">NEXUS 🌐 AI</h1>
</div>
""", unsafe_allow_html=True)

# 检查是否配置了密钥
if not DEEPSEEK_API_KEY or not TAVILY_API_KEY:
    st.error("⚠️ 系统后台未配置 API Key，请联系管理员。")
    st.stop()

# ================= 强制要求输入访问密码 =================
if ACCESS_PASSWORD:
    pwd = st.text_input("🔒 请输入访问密码", type="password")
    if pwd != ACCESS_PASSWORD:
        st.warning("密码错误，无法使用。")
        st.stop()

# ================= 以下为聊天逻辑 =================
HISTORY_FILE = "chat_history.json"

if "messages" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try: st.session_state.messages = json.load(f)
            except: st.session_state.messages = []
    else:
        st.session_state.messages = []

def clean_messages(messages):
    cleaned = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            tool_ids = [tc["id"] for tc in msg["tool_calls"]]
            j = i + 1
            found_tools = []
            while j < len(messages) and messages[j].get("role") == "tool":
                found_tools.append(messages[j])
                j += 1
            found_ids = [t["tool_call_id"] for t in found_tools]
            if set(tool_ids) == set(found_ids):
                cleaned.append(msg)
                cleaned.extend(found_tools)
            i = j
        else:
            cleaned.append(msg)
            i += 1
    return cleaned

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user", avatar="👤").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant", avatar="🌐").write(msg["content"])
        st.markdown("<div class='disclaimer'>本回答由 AI 生成，内容仅供参考，请仔细甄别。</div>", unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("<div class='welcome-text'>嗨！有什么我能帮你的吗？</div>", unsafe_allow_html=True)

prompt = st.chat_input("💬 输入指令，NEXUS 将为你联网检索...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").write(prompt)

    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    tavily = TavilyClient(api_key=TAVILY_API_KEY)

    system_prompt = "你的名字叫'Nexus'，是NEXUS系统的核心智能体。你不是DeepSeek。当用户询问关于实时信息时，你必须优先使用 search_web 工具。"

    tools = [{"type": "function", "function": {"name": "search_web", "description": "搜索互联网以获取最新、实时的信息。", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}]

    try:
        valid_messages = clean_messages(st.session_state.messages)
        response = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}] + valid_messages, tools=tools, tool_choice="auto")
        response_message = response.choices[0].message

        if response_message.tool_calls:
            assistant_msg = {"role": "assistant", "content": response_message.content if response_message.content else "", "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in response_message.tool_calls]}
            st.session_state.messages.append(assistant_msg)

            with st.status("🕵️ NEXUS 正在扫描互联网...", expanded=False) as status:
                for tool_call in response_message.tool_calls:
                    function_args = json.loads(tool_call.function.arguments)
                    search_query = function_args.get("query")
                    st.write(f"🔍 检索目标：`{search_query}` ...")
                    search_result = tavily.search(query=search_query, max_results=3)
                    st.session_state.messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(search_result['results'])})
                status.update(label="✅ 检索完毕，NEXUS 正在生成回复...", state="complete", expanded=False)

            valid_messages = clean_messages(st.session_state.messages)
            with st.chat_message("assistant", avatar="🌐"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}] + valid_messages, stream=True)
                final_answer = st.write_stream(stream)
                st.markdown("<div class='disclaimer'>本回答由 AI 生成，内容仅供参考，请仔细甄别。</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
        else:
            with st.chat_message("assistant", avatar="🌐"):
                stream = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}] + clean_messages(st.session_state.messages), stream=True)
                final_answer = st.write_stream(stream)
                st.markdown("<div class='disclaimer'>本回答由 AI 生成，内容仅供参考，请仔细甄别。</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": final_answer})

        cleaned_history = clean_messages(st.session_state.messages)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"🚨 系统异常：{e}")