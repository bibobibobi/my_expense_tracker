import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="記帳本", page_icon="💰", layout="wide")

# --- 初始化 Session State ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_to_add():
    st.session_state.page = 'add'
    st.rerun()

def go_to_home():
    st.session_state.page = 'home'
    st.rerun()

# --- CSS 與 JS 魔法區 ---
st.markdown("""
<style>
/* 隱藏不必要的元素 */
div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
.block-container { padding-top: 3rem; }

/* 隱藏數字輸入框箭頭 */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type=number] { -moz-appearance: textfield; }

/* 優化手機上的列表顯示 */
div[data-testid="column"] {
    align-self: center; /* 讓內容垂直置中 */
}

/* 讓刪除按鈕變紅色且顯眼 */
button[kind="secondary"] {
    border-color: transparent;
    color: #ff4b4b;
}
button[kind="secondary"]:hover {
    border-color: #ff4b4b;
    background-color: #ffebeb;
}

/* 調整日期標題的間距 */
.date-header {
    font-size: 1.1rem;
    font-weight: bold;
    color: #555;
    margin-top: 15px;
    margin-bottom: 5px;
    border-bottom: 1px solid #eee;
    padding-bottom: 5px;
}
</style>
""", unsafe_allow_html=True)

# JS: 防止手機鍵盤彈出 (日期選擇)
components.html("""
<script>
    window.parent.document.addEventListener('click', () => {
        const dateInputs = window.parent.document.querySelectorAll('div[data-testid="stDateInput"] input');
        dateInputs.forEach(input => {
            input.setAttribute('inputmode', 'none'); 
            input.setAttribute('autocomplete', 'off');
        });
    });
</script>
""", height=0, width=0)

# --- 檔案處理 ---
DATA_FILE = "expenses.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["日期", "項目", "類型", "金額", "備註"])
    df = pd.read_csv(DATA_FILE)
    if "備註" in df.columns:
        df["備註"] = df["備註"].fillna("")
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def delete_record(index_to_delete):
    df = load_data()
    # 確保 index 存在 (避免過濾後 index 對不上的問題)
    if index_to_delete in df.index:
        df = df.drop(index_to_delete)
        save_data(df)
        st.toast("已刪除該筆紀錄", icon="🗑️")
        st.rerun()

# ==========================================
#  頁面 A: 首頁
# ==========================================
def show_home_page():
    df = load_data()
    
    col_header, col_btn = st.columns([7, 3])
    with col_header:
        st.subheader("我的記帳本")
    with col_btn:
        if st.button("➕ 新增", use_container_width=True, type="primary"):
            go_to_add()

    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"])
        
        # --- 儀表板 ---
        total_cash = df[df["類型"] == "現金"]["金額"].sum()
        total_card = df[df["類型"] == "信用卡"]["金額"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("💵 現金", f"${total_cash:,.0f}")
        m2.metric("💳 信用卡", f"${total_card:,.0f}")

        # --- 篩選區 ---
        st.write("") # 空行
        available_months = df["日期"].dt.to_period("M").unique().astype(str)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            selected_month = st.selectbox("月份", options=["所有時間"] + sorted(available_months, reverse=True), label_visibility="collapsed")
        with c2:
            # 簡化顯示，只顯示文字按鈕
            selected_type = st.segmented_control(
                "類型",
                options=["現金", "信用卡"],
                default=["現金", "信用卡"],
                selection_mode="multi",
                label_visibility="collapsed"
            )

        # --- 處理過濾資料 ---
        df_filtered = df.copy()
        
        if selected_month != "所有時間":
            df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]
        
        if not selected_type:
            df_filtered = pd.DataFrame(columns=df.columns)
        else:
            df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]

        # --- [核心修改] 列表顯示邏輯 ---
        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values(by="日期", ascending=False)
            
            # 1. 先抓出所有不重複的日期 (排序過)
            unique_dates = df_filtered["日期"].dt.strftime("%Y-%m-%d").unique()
            
            st.write("") # 加點間距

            # 2. 針對每一天，印出一個區塊
            for date_str in unique_dates:
                # 顯示日期標題
                # 轉換成 datetime 物件來取得星期幾
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday_str = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][date_obj.weekday()]
                
                # 使用 HTML 自定義樣式顯示日期
                st.markdown(f'<div class="date-header">{date_str} ({weekday_str})</div>', unsafe_allow_html=True)
                
                # 3. 抓出這那一天的所有消費
                day_records = df_filtered[df_filtered["日期"].dt.strftime("%Y-%m-%d") == date_str]
                
                for index, row in day_records.iterrows():
                    # 使用 columns 來排版：項目 | 圖示 | 金額 | 刪除
                    # 比例分配：項目佔寬一點，其他固定
                    c_item, c_icon, c_amount, c_del = st.columns([5, 1.5, 2.5, 1.2])
                    
                    with c_item:
                        st.write(f"**{row['項目']}**")
                        if row['備註']:
                            st.caption(row['備註'])
                    
                    with c_icon:
                        # 用 Emoji 代表類型，節省空間
                        icon = "💵" if row['類型'] == "現金" else "💳"
                        st.write(icon)
                        
                    with c_amount:
                        st.write(f"${row['金額']:,}")
                    
                    with c_del:
                        # 每個按鈕需要唯一的 key，我們用 "del_" + index
                        if st.button("✕", key=f"del_{index}", help="刪除此紀錄"):
                            delete_record(index)
                    
                    # 加一條極細的分隔線，區分每一筆
                    st.markdown("<hr style='margin: 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
            
            # 底部留白
            st.write("", "")
            
        else:
            if not selected_type:
                st.warning("請選擇顯示類型")
            else:
                st.info("📭 查無資料")
    else:
        st.info("點擊右上角「新增」開始記帳！")

# ==========================================
#  頁面 B: 新增消費
# ==========================================
def show_add_page():
    # 頂部導航條
    c1, c2 = st.columns([1, 5])
    with c1:
        st.button("⬅", on_click=go_to_home)
    with c2:
        st.subheader("新增消費")
    
    with st.form("add_form", clear_on_submit=True):
        date = st.date_input("日期", datetime.now())
        
        category = st.segmented_control(
            "支付方式", 
            options=["現金", "信用卡"],
            default="現金",
            selection_mode="single"
        )
        
        item = st.text_input("項目", placeholder="例如: 午餐")
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="輸入金額")
        note = st.text_area("備註 (選填)", height=60)
        
        submitted = st.form_submit_button("💾 儲存", type="primary", use_container_width=True)

        if submitted:
            if not category:
                st.error("⚠️ 請選擇支付方式")
            elif item and amount is not None and amount > 0:
                new_data = pd.DataFrame({
                    "日期": [date],
                    "項目": [item],
                    "類型": [category],
                    "金額": [amount],
                    "備註": [note]
                })
                df = load_data()
                df = pd.concat([df, new_data], ignore_index=True)
                save_data(df)
                st.toast(f"已儲存: {item}", icon='✅')
                st.session_state.page = 'home'
                st.rerun()
            else:
                st.error("⚠️ 請輸入項目名稱與金額")

# --- 主程式流程 ---
if st.session_state.page == 'home':
    show_home_page()
elif st.session_state.page == 'add':
    show_add_page()