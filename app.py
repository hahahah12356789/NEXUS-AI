import os
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
import openai
from tavily import TavilyClient
import json

# 关键设置：让侧边栏默认折叠，需要时点左上角箭头展开
st.set_page_config(page_title="NEXUS 🌐 AI", page_icon="🌐", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    :root { --primary-color: #1E40AF; }
    
    .logo-container { text-align: center; margin-top: -30px; margin-bottom: 20px; }
    .welcome-text { text-align: center; color: #94A3B8; font-size: 20px; font-weight: 500; margin-top: 80px; margin-bottom: 40px; }

    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #EBF4FF; border-radius: 15px; border-left: 4px solid #1E40AF; margin-top: 10px;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #F8FAFC; border-radius: 15px; border-left: 4px solid #10B981; margin-top: 10px;
    }

    .disclaimer {
        font-size: 12px !important; color: #94A3B8 !important;
        margin-top: 8px !important; margin-bottom: 4px !important;
        border-top: 1px solid #E2E8F0 !important;
        padding-top: 6px !important; display: inline-block !important;
    }

    .stButton>button {
        background-color: #1E40AF !important; color: white !important;
        border-radius: 8px; border: none; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #1E3A8A !important; }

    div[data-testid="stChatInput"] {
        border: 1.5px solid #CBD5E1 !important; border-radius: 14px !important;
        background-color: #FFFFFF !important; box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
        transition: all 0.3s ease; margin-top: 20px;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #1E40AF !important; box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.2) !important;
    }
    div[data-testid="stChatInput"] textarea:focus { box-shadow: none !important; border: none !important; }

    div[data-testid="stChatInput"] button {
        background-color: #1E40AF !important; color: white !important;
        border-radius: 50% !important; width: 38px !important; height: 38px !important;
        padding: 0 !important; display: flex !important; align-items: center !important;
        justify-content: center !important; margin-right: 4px !important; border: none !important;
        transition: all 0.3s ease;
    }
    div[data-testid="stChatInput"] button:hover { background-color: #1E3A8A !important; transform: scale(1.05); }
    div[data-testid="stChatInput"] button svg { fill: white !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

HISTORY_FILE = "chat_history.json"
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_config(api_key, tavily_key):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"api_key": api_key, "tavily_key": tavily_key}, f, ensure_ascii=False, indent=2)

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

if "messages" not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try: st.session_state.messages = json.load(f)
            except: st.session_state.messages = []
    else:
        st.session_state.messages = []

if "api_key" not in st.session_state or "tavily_key" not in st.session_state:
    config = load_config()
    st.session_state.api_key = config.get("api_key", "")
    st.session_state.tavily_key = config.get("tavily_key", "")

# ================= 侧边栏（设置在固定侧边栏里，绝不滚动） =================
with st.sidebar:
    st.header("⚙️ 设置")
    st.markdown("### 🔑 API 密钥")
    sidebar_api_key = st.text_input("DeepSeek API Key", type="password", value=st.session_state.api_key)
    sidebar_tavily_key = st.text_input("Tavily API Key", type="password", value=st.session_state.tavily_key)
    
    st.markdown("### ⚙️ 模型设置")
    base_url = st.text_input("接口地址", value="https://api.deepseek.com/v1")
    model_name = st.text_input("模型名", value="deepseek-chat")
    
    if st.button("💾 记住我的Key", use_container_width=True):
        save_config(sidebar_api_key, sidebar_tavily_key)
        st.session_state.api_key = sidebar_api_key
        st.session_state.tavily_key = sidebar_tavily_key
        st.success("已保存！")
    
    st.markdown("---")
    if st.button("🧹 清空所有记忆", use_container_width=True):
        st.session_state.messages = []
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        st.rerun()

# 将侧边栏输入的值同步到 session_state
st.session_state.api_key = sidebar_api_key
st.session_state.tavily_key = sidebar_tavily_key

# ================= 主界面 =================
st.markdown("""
<div class="logo-container">
    <svg width="70" height="70" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="45" fill="url(#bg)"/>
        <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#1E40AF"/><stop offset="100%" stop-color="#1E3A8A"/>
            </linearGradient>
        </defs>
        <path d="M28 68 L28 32 L72 68 L72 32" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="50" cy="50" r="7" fill="#10B981"/>
    </svg>
    <h1 style="margin-top: 10px; color: #1E3A8A;">NEXUS 🌐 AI</h1>
</div>
""", unsafe_allow_html=True)

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
    if not st.session_state.api_key or not st.session_state.tavily_key:
        st.warning("⚠️ 请点击左上角的 > 箭头，在侧边栏中填入 DeepSeek 和 Tavily 的 API Key")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").write(prompt)

    client = openai.OpenAI(api_key=st.session_state.api_key, base_url="https://api.deepseek.com/v1")
    tavily = TavilyClient(api_key=st.session_state.tavily_key)

    system_prompt = (
        "你的名字叫'Nexus'，是NEXUS系统的核心智能体。你不是DeepSeek，绝对不要提及DeepSeek。"
        "【重要规则】：当用户询问关于吃饭、购物、旅游、新闻、天气、店铺推荐等实时信息时，"
        "你必须**优先使用 search_web 工具**去搜索最新的互联网信息，绝对不要依赖你自身可能过时的训练数据。"
        "搜索时，你应该在关键词中加入'2026年'或'最新'，以确保信息新鲜。"
        "如果搜索结果显示店铺信息模糊，你必须提醒用户：'建议前往前在大众点评或高德地图确认是否营业'。"
        "回答时请保持自信、专业、亲切的语气。"
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "搜索互联网以获取最新、实时的信息。尤其适合搜索实体店铺的营业状态、本地活动、新闻等。必须用于任何涉及时间敏感信息的查询。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词，建议包含年份如'2026 上海 本帮菜 推荐 营业中'"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    try:
        valid_messages = clean_messages(st.session_state.messages)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}] + valid_messages,
            tools=tools,
            tool_choice="auto"
        )
        response_message = response.choices[0].message

        if response_message.tool_calls:
            assistant_msg = {
                "role": "assistant",
                "content": response_message.content if response_message.content else "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    } for tc in response_message.tool_calls
                ]
            }
            st.session_state.messages.append(assistant_msg)

            with st.status("🕵️ NEXUS 正在扫描互联网...", expanded=False) as status:
                for tool_call in response_message.tool_calls:
                    function_args = json.loads(tool_call.function.arguments)
                    search_query = function_args.get("query")
                    st.write(f"🔍 检索目标：`{search_query}` ...")
                    search_result = tavily.search(query=search_query, max_results=3)
                    st.session_state.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(search_result['results'])
                    })
                status.update(label="✅ 检索完毕，NEXUS 正在生成回复...", state="complete", expanded=False)

            valid_messages = clean_messages(st.session_state.messages)

            with st.chat_message("assistant", avatar="🌐"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": system_prompt}] + valid_messages,
                    stream=True
                )
                final_answer = st.write_stream(stream)
                st.markdown("<div class='disclaimer'>本回答由 AI 生成，内容仅供参考，请仔细甄别。</div>", unsafe_allow_html=True)
            
            st.session_state.messages.append({"role": "assistant", "content": final_answer})
            
        else:
            with st.chat_message("assistant", avatar="🌐"):
                stream = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": system_prompt}] + clean_messages(st.session_state.messages),
                    stream=True
                )
                final_answer = st.write_stream(stream)
                st.markdown("<div class='disclaimer'>本回答由 AI 生成，内容仅供参考，请仔细甄别。</div>", unsafe_allow_html=True)
                
            st.session_state.messages.append({"role": "assistant", "content": final_answer})

        cleaned_history = clean_messages(st.session_state.messages)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_history, f, ensure_ascii=False, indent=2)

    except Exception as e:
        st.error(f"🚨 系统异常：{e}")
        st.info("💡 提示：如果网络断开，请点击左上角箭头，清理记忆并重试。")