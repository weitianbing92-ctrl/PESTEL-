import streamlit as st
from openai import OpenAI
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="PESTEL 模拟器", page_icon="🌍")

# --- 2. 初始化配置 (优先读取 Secrets) ---
# 这里会自动读取你在 Streamlit Cloud 后台设置的 Secrets
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    base_url = st.secrets.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # 关键修改：读取你设置的 ep-xxxxx 模型ID，如果没有则默认 gpt-3.5-turbo
    model_id = st.secrets.get("MODEL", "gpt-3.5-turbo")
    is_student_mode = True # 标记为学生模式（无需输入key）
else:
    api_key = ""
    base_url = "https://api.openai.com/v1"
    model_id = "gpt-3.5-turbo"
    is_student_mode = False

# --- 3. 初始化游戏状态 ---
if "messages" not in st.session_state:
    system_prompt = """
    你是一个国际商务模拟游戏的主持人。玩家是一家电动滑板车公司的 CEO，目标是进入虚构国家"梅里迪亚"。
    
    你的任务：
    1. 根据 PESTEL 模型（政治、经济、社会、技术、环境、法律），每回合给玩家出一个具体的商业难题。
    2. 必须给出 3 个选项 (A, B, C)，每个选项都有风险和收益。
    3. 玩家做出选择后，你要根据选择判定结果（资金增减、市场份额变化），并给出简短的点评。
    4. 然后立即进入下一个 PESTEL 维度的难题。
    
    初始资金：1000万。
    请保持语气专业、紧凑。
    
    第一关：请从【政治 (Political)】因素开始，描述大选可能带来的关税风险。
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]

if "money" not in st.session_state:
    st.session_state.money = 1000
if "turn" not in st.session_state:
    st.session_state.turn = 1

# --- 4. 侧边栏 ---
with st.sidebar:
    st.header("🎮 控制面板")
    
    # 如果不是学生模式（本地运行且没配secret），才显示输入框
    if not is_student_mode:
        api_key = st.text_input("请输入 API Key", type="password")
        base_url = st.text_input("Base URL", value="https://api.openai.com/v1")
        model_id = st.text_input("模型 ID", value="gpt-3.5-turbo")
    else:
        st.success("✅ 已连接学校服务器")
        st.info(f"当前引擎: 火山引擎 (Doubao)")

    st.divider()
    st.subheader("📊 公司状态")
    st.metric(label="可用资金", value=f"${st.session_state.money} 万")
    st.metric(label="当前回合", value=f"第 {st.session_state.turn} 关")
    
    if st.button("🔄 重置游戏"):
        st.session_state.clear()
        st.rerun()

# --- 5. AI 核心逻辑 ---
def get_ai_response(user_input):
    if not api_key:
        return "⚠️ 未检测到 API Key。请检查后台 Secrets 配置。"
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    try:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        response = client.chat.completions.create(
            model=model_id,  # 这里现在会使用你设置的 ep-xxxx
            messages=st.session_state.messages,
            temperature=0.7
        )
        
        ai_content = response.choices[0].message.content
        return ai_content
        
    except Exception as e:
        return f"🚫 连接错误: {str(e)}"

# --- 6. 主界面 ---
st.title("🌍 PESTEL 商业实战模拟")

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 自动开场
if len(st.session_state.messages) == 1:
    with st.chat_message("assistant"):
        with st.spinner("正在接入全球商业数据库..."):
            response = get_ai_response("游戏开始。")
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# 用户交互
if prompt := st.chat_input("做出你的决策 (输入 A/B/C)"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("董事会正在评估..."):
            response = get_ai_response(prompt)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # 简单的数值反馈逻辑
            if "资金减少" in response or "亏损" in response:
                st.session_state.money -= 50
            elif "盈利" in response or "资金增加" in response:
                st.session_state.money += 50
            
            st.session_state.turn += 1
            st.rerun()
