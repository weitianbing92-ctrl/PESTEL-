import streamlit as st
from openai import OpenAI
import json
import re

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="PESTEL 商业大亨", page_icon="🌍", layout="wide")

st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 初始化配置 (读取 Secrets) ---
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    base_url = st.secrets.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_id = st.secrets.get("MODEL", "gpt-3.5-turbo")
else:
    api_key = ""
    base_url = "https://api.openai.com/v1"
    model_id = "gpt-3.5-turbo"

# --- 3. 初始化游戏状态 ---
if "history" not in st.session_state:
    st.session_state.history = [] 
if "money" not in st.session_state:
    st.session_state.money = 1000 
if "market_share" not in st.session_state:
    st.session_state.market_share = 0 
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "current_options" not in st.session_state:
    st.session_state.current_options = None 

# --- 4. 核心 AI 逻辑 (手动清洗 JSON) ---
def get_ai_response(user_choice=None):
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # 提示词：强调只输出纯 JSON
    system_prompt = """
    你是一个【PESTEL 国际商务模拟游戏引擎】。
    请务必只返回一个标准的 JSON 格式字符串，不要包含任何 Markdown 标记（如 ```json）。
    不要输出任何其他解释性文字。
    
    回复格式必须包含：
    {
        "story": "剧情描述（100字以内）",
        "money_change": 整数 (例如 -50 或 100),
        "market_share_change": 整数 (例如 5 或 -2),
        "analysis": "商业分析",
        "next_pestel": "当前 PESTEL 维度",
        "options": [
            {"id": "A", "text": "选项A描述"},
            {"id": "B", "text": "选项B描述"},
            {"id": "C", "text": "选项C描述"}
        ]
    }
    每一关切换一个 PESTEL 维度。
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # 压缩历史记录
    for entry in st.session_state.history[-3:]:
        # 为了节省 token，我们只发简化的历史
        simple_entry = {
            "story": entry['raw_json'].get('story'),
            "user_choice": entry.get('user_choice')
        }
        messages.append({"role": "assistant", "content": json.dumps(simple_entry)})
    
    if user_choice:
        messages.append({"role": "user", "content": f"我选择了: {user_choice}"})
    else:
        messages.append({"role": "user", "content": "游戏开始。"})

    try:
        # 调用 API (移除了 response_format 参数)
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7
        )
        content = response.choices[0].message.content
        
        # --- 关键修复：手动清洗数据 ---
        # 有时候模型会返回 ```json {...} ```，我们需要用正则把它提取出来
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            clean_json = match.group()
            return json.loads(clean_json)
        else:
            # 如果实在没找到 JSON，抛出异常
            raise ValueError("AI 未返回有效的 JSON 格式")
            
    except Exception as e:
        st.error(f"数据解析错误: {e}")
        st.caption("原始内容: " + (content if 'content' in locals() else "无"))
        return None

# --- 5. 界面布局 ---

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 公司资金", f"${st.session_state.money} 万")
with col2:
    st.metric("📈 市场份额", f"{st.session_state.market_share}%")
with col3:
    if st.button("🔄 重置游戏"):
        st.session_state.clear()
        st.rerun()

st.divider()

# 自动开始
if not st.session_state.history:
    with st.spinner("正在加载全球市场数据..."):
        data = get_ai_response()
        if data:
            st.session_state.history.append({"raw_json": data})
            st.session_state.current_options = data.get('options')
            st.rerun()

# 历史回放
for i, turn in enumerate(st.session_state.history):
    data = turn['raw_json']
    with st.container():
        st.subheader(f"第 {i+1} 关: {data.get('next_pestel', '挑战')}")
        
        if i > 0:
            c1, c2 = st.columns(2)
            money_chg = data.get('money_change', 0)
            share_chg = data.get('market_share_change', 0)
            with c1:
                if money_chg != 0:
                    st.info(f"资金: {money_chg}万 | 分析: {data.get('analysis')}")
            with c2:
                if share_chg != 0:
                    st.success(f"市场份额: {'+' if share_chg>0 else ''}{share_chg}%")

        st.write(data.get('story'))
        
        if 'user_choice' in turn:
            st.caption(f"🏁 你的决策: 选项 {turn['user_choice']}")
        st.divider()

# 按钮区
if not st.session_state.game_over and st.session_state.current_options:
    st.markdown("### ⚡ 请做出你的战略决策")
    opts = st.session_state.current_options
    
    # 容错处理：确保 AI 真的返回了3个选项
    if len(opts) >= 3:
        b1, b2, b3 = st.columns(3)
        
        def make_choice(cid):
            st.session_state.history[-1]['user_choice'] = cid
            with st.spinner("推演中..."):
                new_data = get_ai_response(cid)
                if new_data:
                    st.session_state.money += new_data.get('money_change', 0)
                    st.session_state.market_share += new_data.get('market_share_change', 0)
                    st.session_state.history.append({"raw_json": new_data})
                    st.session_state.current_options = new_data.get('options')
                    if st.session_state.money <= 0:
                        st.session_state.game_over = True
                        st.error("💸 破产！游戏结束。")

        with b1:
            if st.button(f"A. {opts[0]['text']}"):
                make_choice("A")
                st.rerun()
        with b2:
            if st.button(f"B. {opts[1]['text']}"):
                make_choice("B")
                st.rerun()
        with b3:
            if st.button(f"C. {opts[2]['text']}"):
                make_choice("C")
                st.rerun()
    else:
        st.warning("AI 返回的选项不足，正在重试...")
        st.rerun()

if st.session_state.game_over:
    st.error("GAME OVER - 请点击顶部的重置按钮")
