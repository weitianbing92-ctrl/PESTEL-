import streamlit as st
from openai import OpenAI
import json
import re

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="PESTEL 商业大亨", page_icon="🌍", layout="wide")

# 引入自定义 CSS 让界面更漂亮
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
    # 本地测试用的空值，防止报错
    api_key = ""
    base_url = "https://api.openai.com/v1"
    model_id = "gpt-3.5-turbo"

# --- 3. 初始化游戏状态 ---
if "history" not in st.session_state:
    st.session_state.history = [] # 存储游戏剧情
if "money" not in st.session_state:
    st.session_state.money = 1000 # 初始资金
if "market_share" not in st.session_state:
    st.session_state.market_share = 0 # 市场占有率
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "current_options" not in st.session_state:
    st.session_state.current_options = None # 存储当前的三个选项

# --- 4. 核心 AI 逻辑 (强制 JSON 输出) ---
def get_ai_response(user_choice=None):
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # 构建 Prompt
    system_prompt = """
    你是一个【PESTEL 国际商务模拟游戏引擎】。
    你需要以严格的 JSON 格式回复，不要包含任何 markdown 标记。
    
    回复格式必须包含以下字段：
    {
        "story": "当前发生的剧情描述（100字以内）",
        "money_change": 整数 (例如 -50 或 100, 根据上一步玩家选择导致的结果),
        "market_share_change": 整数 (例如 5 或 -2, 表示市场份额百分比变化),
        "analysis": "对上一步选择的简短商业分析",
        "next_pestel": "当前面临的 PESTEL 维度 (例如 '政治 Political')",
        "options": [
            {"id": "A", "text": "选项A的具体描述"},
            {"id": "B", "text": "选项B的具体描述"},
            {"id": "C", "text": "选项C的具体描述"}
        ]
    }
    
    如果是游戏刚开始，money_change 和 market_share_change 为 0。
    每一关都切换一个不同的 PESTEL 维度。
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # 将历史剧情压缩后发给 AI (保留最近 3 轮以节省 token)
    for entry in st.session_state.history[-3:]:
        messages.append({"role": "assistant", "content": json.dumps(entry['raw_json'])})
        if 'user_choice' in entry:
            messages.append({"role": "user", "content": f"我选择了: {entry['user_choice']}"})
    
    if user_choice:
        messages.append({"role": "user", "content": f"我选择了: {user_choice}"})
    else:
        messages.append({"role": "user", "content": "游戏开始，请给出第一个场景。"})

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7,
            response_format={ "type": "json_object" } # 强制 JSON 模式 (如果模型支持)
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        st.error(f"AI 数据解析失败: {e}")
        return None

# --- 5. 界面布局 ---

# 顶栏：仪表盘
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 公司资金", f"${st.session_state.money} 万", delta=None)
with col2:
    st.metric("📈 市场份额", f"{st.session_state.market_share}%")
with col3:
    if st.button("🔄 重置游戏"):
        st.session_state.clear()
        st.rerun()

st.divider()

# 主游戏区
if not st.session_state.history:
    # 游戏还没开始，自动触发第一轮
    with st.spinner("正在加载全球市场数据..."):
        data = get_ai_response()
        if data:
            st.session_state.history.append({"raw_json": data})
            st.session_state.current_options = data['options']
            st.rerun()

# 显示历史剧情
for i, turn in enumerate(st.session_state.history):
    data = turn['raw_json']
    
    # 显示 AI 的剧情卡片
    with st.container():
        # 标题栏
        st.subheader(f"第 {i+1} 关: {data.get('next_pestel', '开始')}")
        
        # 如果有资金变动，显示反馈
        if i > 0: # 第一关不显示变动
            c1, c2 = st.columns(2)
            money_change = data.get('money_change', 0)
            share_change = data.get('market_share_change', 0)
            
            with c1:
                if money_change != 0:
                    st.info(f"资金变动: {money_change}万 | 分析: {data.get('analysis', '')}")
            with c2:
                if share_change != 0:
                    st.success(f"市场份额: {'+' if share_change>0 else ''}{share_change}%")

        # 剧情内容
        st.write(data.get('story', ''))
        
        # 显示用户当时的选择 (如果是历史记录)
        if 'user_choice' in turn:
            st.caption(f"🏁 你做出的决策: 选项 {turn['user_choice']}")
        
        st.divider()

# 底部：操作区 (只有当游戏未结束且有选项时显示)
if not st.session_state.game_over and st.session_state.current_options:
    st.markdown("### ⚡ 请做出你的战略决策")
    
    opts = st.session_state.current_options
    
    # 使用 3 列布局放置按钮
    b1, b2, b3 = st.columns(3)
    
    def on_click(choice_id):
        # 记录用户选择
        st.session_state.history[-1]['user_choice'] = choice_id
        
        # 获取下一轮结果
        with st.spinner("正在推演决策后果..."):
            new_data = get_ai_response(choice_id)
            if new_data:
                # 更新数值
                st.session_state.money += new_data.get('money_change', 0)
                st.session_state.market_share += new_data.get('market_share_change', 0)
                
                # 存入历史
                st.session_state.history.append({"raw_json": new_data})
                st.session_state.current_options = new_data.get('options', [])
                
                # 检查是否破产
                if st.session_state.money <= 0:
                    st.session_state.game_over = True
                    st.error("💸 资金链断裂！公司破产了。")
        
    # 渲染三个按钮
    with b1:
        if st.button(f"A. {opts[0]['text']}"):
            on_click("A")
            st.rerun()
    with b2:
        if st.button(f"B. {opts[1]['text']}"):
            on_click("B")
            st.rerun()
    with b3:
        if st.button(f"C. {opts[2]['text']}"):
            on_click("C")
            st.rerun()

# 游戏结束状态
if st.session_state.game_over:
    st.error("GAME OVER - 请点击顶部的重置按钮重新开始")
