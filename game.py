import streamlit as st
from openai import OpenAI
import json

# --- 1. 页面配置 ---
st.set_page_config(page_title="PESTEL 模拟器", page_icon="🌍")

# --- 2. 初始化游戏状态 (Session State) ---
# Streamlit 会在每次交互时刷新，所以我们需要把数据保存在 session_state 中
if "messages" not in st.session_state:
    # 初始提示词 (System Prompt)：这是游戏的灵魂，告诉 AI 怎么玩
    system_prompt = """
    你是一个国际商务模拟游戏的主持人。玩家是一家电动滑板车公司的 CEO，目标是进入虚构国家"梅里迪亚"。

    你的任务：
    1. 根据 PESTEL 模型（政治、经济、社会、技术、环境、法律），每回合给玩家出一个具体的商业难题。
    2. 必须给出 3 个选项 (A, B, C)，每个选项都有风险和收益。
    3. 玩家做出选择后，你要根据选择判定结果（资金增减、市场份额变化），并给出简短的点评。
    4. 然后立即进入下一个 PESTEL 维度的难题。

    初始资金：1000万。
    请保持语气专业、紧凑，并在回复末尾明确列出 updated_money (数值) 用于系统更新。

    第一关：请从【政治 (Political)】因素开始，描述大选可能带来的关税风险。
    """
    st.session_state.messages = [{"role": "system", "content": system_prompt}]

if "money" not in st.session_state:
    st.session_state.money = 1000  # 单位：万
if "turn" not in st.session_state:
    st.session_state.turn = 1

# --- 3. 侧边栏：设置与状态 ---
with st.sidebar:
    st.header("🎮 控制面板")

    # 获取 API Key (为了安全，建议让用户输入，或者你自己在代码里写死)
    # --- 修改后的代码：优先读取云端配置的 Key，如果没有再让用户输入 ---
with st.sidebar:
    st.header("🎮 控制面板")
    
    # 尝试从 Secrets 读取 Key (用于云端部署)
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        # 如果 secrets 里配置了 url 就用配置的，否则默认
        base_url = st.secrets.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        st.success("✅ 已连接教师提供的 AI 引擎")
    else:
        # 本地运行时让用户输入
        api_key = st.text_input("请输入大模型 API Key", type="password")
        base_url = st.text_input("Base URL", value="https://api.openai.com/v1")

    st.divider()

    st.subheader("📊 公司状态")
    st.metric(label="可用资金", value=f"${st.session_state.money} 万")
    st.metric(label="当前回合", value=f"第 {st.session_state.turn} 关")

    if st.button("🔄 重置游戏"):
        st.session_state.clear()
        st.rerun()


# --- 4. 核心功能：调用 AI ---
def get_ai_response(user_input):
    """
    发送历史对话给 AI，获取下一步剧情
    """
    if not api_key:
        return "⚠️ 请在侧边栏输入 API Key 才能启动 AI 大脑。（如果你没有 Key，这是一个演示回复：请假装你选了 A，但真正的游戏需要 API 支持）"

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        # 将用户的新选择加入历史
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 调用大模型
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 或者其他模型名称，如 deepseek-chat
            messages=st.session_state.messages,
            temperature=0.7
        )

        ai_content = response.choices[0].message.content
        return ai_content

    except Exception as e:
        return f"🚫 AI 连接错误: {str(e)}"


# --- 5. 主界面：聊天窗口 ---
st.title("🌍 PESTEL 商业实战模拟")
st.caption("作为 CEO，利用 PESTEL 框架征服新兴市场。")

# 显示历史聊天记录
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 6. 游戏开场自动触发 ---
# 如果历史记录只有 system prompt 一条，说明游戏刚开始，需要 AI 先说话
if len(st.session_state.messages) == 1:
    with st.chat_message("assistant"):
        with st.spinner("正在分析梅里迪亚局势..."):
            # 这里我们手动触发第一次 AI 发言，或者发送一个空指令让 AI 开始
            initial_trigger = "游戏开始。请给出第一个政治(Political)场景。"
            response = get_ai_response(initial_trigger)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- 7. 用户输入处理 ---
if prompt := st.chat_input("做出你的决策 (输入 A/B/C)"):
    # 1. 显示用户输入
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 获取 AI 回复
    with st.chat_message("assistant"):
        with st.spinner("AI 正在推演后果..."):
            response = get_ai_response(prompt)
            st.markdown(response)

            # 3. 更新历史
            st.session_state.messages.append({"role": "assistant", "content": response})

            # 4. (可选) 简单的数值提取逻辑 - 实际开发中可以让 AI 返回 JSON 格式以便精准解析
            if "资金减少" in response or "亏损" in response:
                st.session_state.money -= 50
            elif "盈利" in response or "资金增加" in response:
                st.session_state.money += 50

            st.session_state.turn += 1

            st.rerun()  # 刷新页面以更新侧边栏数值
