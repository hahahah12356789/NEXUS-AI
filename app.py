import streamlit as st
import openai
from PyPDF2 import PdfReader
import os

st.set_page_config(page_title="带权限的AI知识库", layout="wide")
st.title("📚 带权限的AI知识库")

# 初始化 session state 保存文档内容
if "doc_text" not in st.session_state:
    st.session_state.doc_text = ""

with st.sidebar:
    st.header("1. 身份认证")
    role = st.selectbox("请选择你的角色", ["普通员工", "管理员"])
    
    st.header("2. 填你的钥匙")
    api_key = st.text_input("输入你的API Key", type="password")
    base_url = st.text_input("输入接口地址", value="https://api.deepseek.com/v1")
    model_name = st.text_input("模型名", value="deepseek-chat")

    # 权限控制：只有管理员才能上传文档
    if role == "管理员":
        st.header("3. 上传文档（仅管理员）")
        uploaded_file = st.file_uploader("上传PDF或TXT", type=["pdf", "txt"])
        if uploaded_file is not None:
            with st.spinner("正在读文档..."):
                try:
                    if uploaded_file.type == "application/pdf":
                        reader = PdfReader(uploaded_file)
                        raw_text = "".join([page.extract_text() for page in reader.pages])
                    else:
                        raw_text = str(uploaded_file.read(), "utf-8")
                    
                    if len(raw_text) > 10000:
                        raw_text = raw_text[:10000] + "...(截断)"
                    
                    st.session_state.doc_text = raw_text
                    st.success(f"文档已读取，共{len(raw_text)}字符")
                except Exception as e:
                    st.error(f"读文件出错：{e}")
    else:
        if not st.session_state.doc_text:
            st.warning("普通员工无法上传文档。目前知识库为空，请等待管理员上传。")
        else:
            st.info("文档已就绪（由管理员上传），你可以开始提问了。")

# 问答逻辑
if api_key and st.session_state.doc_text:
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    st.header("开始提问")
    question = st.text_input("输入你的问题")
    
    if question:
        with st.spinner("思考中..."):
            prompt = f"基于以下内容回答问题，如果内容中没有答案，请说'未找到相关信息'。\n\n内容：\n{st.session_state.doc_text}\n\n问题：{question}\n\n回答："
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                answer = response.choices[0].message.content
                st.write("回答：", answer)
            except Exception as e:
                st.error(f"调用模型出错：{e}")
                if "402" in str(e) or "Insufficient Balance" in str(e):
                    st.warning("⚠️ 你的 DeepSeek 账号余额不足，请充值或更换平台。")
else:
    if not api_key:
        st.warning("请在左边填上你的API Key")
    elif not st.session_state.doc_text and role == "管理员":
        st.info("请在左边上传文档，然后开始提问。")