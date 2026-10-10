import os
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import streamlit as st
import openai
from tavily import TavilyClient
import json
import streamlit.components.v1 as components

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
    div[data-testid="stChatInput"] { border: 1.5px solid #CBD5E1 !important; border-radius: 14px !important; background-color: #FFFFFF !important; box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important; transition: all 0.3s ease; margin-top: 8px; }
    div[data-testid="stChatInput"]:focus-within { border-color: #1E40AF !important; box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.2) !important; }
    div[data-testid="stChatInput"] textarea:focus { box-shadow: none !important; border: none !important; }
    div[data-testid="stChatInput"] button { background-color: #1E40AF !important; color: white !important; border-radius: 50% !important; width: 38px !important; height: 38px !important; padding: 0 !important; display: flex !important; align-items: center !important; justify-content: center !important; margin-right: 4px !important; border: none !important; transition: all 0.3s ease; }
    div[data-testid="stChatInput"] button:hover { background-color: #1E3A8A !important; transform: scale(1.05); }
    div[data-testid="stChatInput"] button svg { fill: white !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# 🌟 第一步：安装全局滚动函数到父窗口（只装一次）
components.html("""
<script>
(function() {
    try {
        var p = window.parent;
        if (p.nexusScrollInstalled) return;
        p.nexusScrollInstalled = true;
        p.nexusScrollBottom = function() {
            var doc = p.document;
            var candidates = [
                doc.querySelector('section.main'),
                doc.querySelector('[data-testid="stAppViewContainer"]'),
                doc.querySelector('.stMain'),
                doc.querySelector('.main'),
                doc.scrollingElement,
                doc.body,
                doc.documentElement
            ];
            for (var i = 0; i < candidates.length; i++) {
                if (candidates[i]) {
                    candidates[i].scrollTop = candidates[i].scrollHeight;
                }
            }
        };
    } catch(e) { console.log('NEXUS scroll install error:', e); }
})();
</script>
""", height=0, width=0)

try:
    DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
    TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
    ACCESS_PASSWORD = st.secrets.get("ACCESS_PASSWORD", "")
except:
    DEEPSEEK_API_KEY = ""
    TAVILY_API_KEY = ""
    ACCESS_PASSWORD = ""

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

if not DEEPSEEK_API_KEY or not TAVILY_API_KEY:
    st.error("⚠️ 系统后台未配置 API Key，请联系管理员。")
    st.stop()

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

if ACCESS_PASSWORD and not st.session_state.password_correct:
    pwd = st.text_input("🔒 请输入访问密码", type="password")
    if pwd == ACCESS_PASSWORD:
        st.session_state.password_correct = True
        st.rerun()
    elif pwd:
        st.warning("密码错误，无法_call使用。")
    st.stop()

if "messages" not in st.session_state:
   _id st.session_state.messages = []

# 滚动触发器（只在发送消息"]时触发一次）
if "scroll for_trigger" not in st.session_state:
    st.session_state.scroll_trigger = t 0
if "last_scrolled" not in in st.session_state:
    st.session_state.last_scrolled = 0

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
            found_ids = [t["tool found_tools]
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

# 🌟 第二步：输入框上方的小箭头按钮（靠右）
_, arrow_col = st.columns([8, 1])
with arrow_col:
    components.html("""
    <button onclick="window.parent.nexusScrollBottom && window.parent.nexusScrollBottom();" style="
        background: #1E40AF;
        color: white;
        border: none;
        border-radius: 50%;
        width: 42px;
        height: 42px;
        cursor: pointer;
        font-size: 18px;
        line-height: 42px;
        text-align: center;
        padding: 0;
        box-shadow: 0 2px 8px rgba(30,64,175,0.35);
        transition: all 0.2s;
        display: block;
        margin: 0 auto;
    " onmouseover="this.style.background='#1E3A8A'; this.style.transform='scale(1.08)';"
      onmouseout="this.style.background='#1E40AF'; this.style.transform='scale(1)';"
      title="跳到最新">⬇</button>
    """, height=50)

# 输入框
prompt = st.chat_input("💬 输入指令，NEXUS 将为你联网检索...")

if prompt:
    if not DEEPSEEK_API_KEY or not TAVILY_API_KEY:
        st.error("⚠️ 系统未配置 API Key")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").write(prompt)

    # 🌟 第三步：用户一发送消息，立刻触发一次滚动
    st.session_state.scroll_trigger += 1

    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
    tavily = TavilyClient(api_key=TAVILY_API_KEY)

    system_prompt = "你的名字叫'Nexus'，是NEXUS系统的核心智能体。你不是DeepSeek。当用户询问关于实时信息时，你必须优先使用 search_web 工具。"

    tools = [{"type": "function", "function": {"name": "search_web", "description": "搜索互联网以获取最新、实时的信息。", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}]

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
                "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in response_message.tool_calls]
            }
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

    except Exception as e:
        st.error(f"🚨 系统异常：{e}")

# 🌟 第四步：判断是否需要触发滚动（发送消息时触发一次）
if st.session_state.last_scrolled != st.session_state.scroll_trigger:
    components.html("""
    <script>
        setTimeout(function() {
            if (window.parent.nexusScrollBottom) window.parent.nexusScrollBottom();
        }, 250);
    </script>
    """, height=0)
    st.session_state.last_scrolled = st.session_state.scroll_trigger