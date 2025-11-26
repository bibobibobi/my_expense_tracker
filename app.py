import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import uuid # 引入 UUID 來產生唯一 ID
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

/* 日期標題樣式 */
.date-header {
    font-size: 1.0rem;
    font-weight: bold;
    color: #444;
    background-color: #f0f2f6;
    padding: 8px 12px;
    border-radius: 8px;
    margin-top: 20px;
    margin-bottom: 8px;
}

/* 列表項目文字樣式 */
.list-item-text {
    font-size: 1rem;
    line-height: 1.5;
}
.list-item-sub {
    font-size: 0.8rem;
    color: #888;
}

/* 調整 Checkbox 大小與位置，讓它好按一點 */
div[data-testid="stCheckbox"] {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

# JS: 防止手機鍵盤彈出
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

# --- 檔案處理 (含 ID 遷移邏輯) ---
DATA_FILE = "expenses.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["ID", "日期", "項目", "類型", "金額", "備註"])
    
    df = pd.read_csv(DATA_FILE)
    
    # [修復] 資料遷移：確保舊資料也有 ID
    if "ID" not in df.columns:
        # 為每一列產生一個新的 UUID
        df["ID"] = [str(uuid.uuid4()) for _ in range(len(df))]
        save_data(df)
        
    if "備註" in df.columns:
        df["備註"] = df["備註"].fillna("")
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def delete_record(record_id):
    df = load_data()
    # 使用 ID 來刪除，而不是 Index
    df = df[df["ID"] != record_id]
    save_data(df)
    st.toast("已刪除", icon="🗑️")
    st.rerun()

# ==========================================
#  頁面 A: 首頁
# ==========================================
def show_home_page():
    df = load_data()
    
    # 標題區
    col_header, col_btn = st.columns([7, 3], vertical_alignment="center")
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
        st.write("")
        available_months = df["日期"].dt.to_period("M").unique().astype(str)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            selected_month = st.selectbox("月份", options=["所有時間"] + sorted(available_months, reverse=True), label_visibility="collapsed")
        with c2:
            selected_type = st.segmented_control(
                "類型",
                options=["現金", "信用卡"],
                default=["現金", "信用卡"],
                selection_mode="multi",
                label_visibility="collapsed"
            )

        # --- 列表顯示邏輯 ---
        df_filtered = df.copy()
        
        if selected_month != "所有時間":
            df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]
        
        if not selected_type:
            df_filtered = pd.DataFrame(columns=df.columns)
        else:
            df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]

        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values(by="日期", ascending=False)
            unique_dates = df_filtered["日期"].dt.strftime("%Y-%m-%d").unique()
            
            st.write("") 

            for date_str in unique_dates:
                # 1. 顯示日期標題 (單獨一行)
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday_str = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][date_obj.weekday()]
                st.markdown(f'<div class="date-header">{date_str} ({weekday_str})</div>', unsafe_allow_html=True)
                
                # 2. 顯示當天的紀錄
                day_records = df_filtered[df_filtered["日期"].dt.strftime("%Y-%m-%d") == date_str]
                
                for _, row in day_records.iterrows():
                    # [重點修改] 版面配置：改為兩欄，確保手機不換行
                    # 左邊 (85%)：所有文字資訊 (類型 + 項目 + 金額)
                    # 右邊 (15%)：刪除框
                    c_info, c_del = st.columns([5.5, 1], vertical_alignment="center")
                    
                    record_id = row['ID']
                    
                    with c_info:
                        # 組合字串：圖示 | 項目 | 金額
                        icon = "💵" if row['類型'] == "現金" else "💳"
                        # 備註處理
                        note_html = f"<div class='list-item-sub'>{row['備註']}</div>" if row['備註'] else ""
                        
                        # 使用 HTML 渲染讓它們在同一行
                        st.markdown(
                            f"""
                            <div class="list-item-text">
                                {icon} &nbsp; <b>{row['項目']}</b> &nbsp; <code>${row['金額']:,}</code>
                            </div>
                            {note_html}
                            """, 
                            unsafe_allow_html=True
                        )

                    with c_del:
                        # [重點修復] Key 使用唯一的 ID，避免刪除後勾選狀態錯亂
                        is_checked = st.checkbox("刪", key=f"chk_{record_id}", label_visibility="collapsed")
                    
                    # 確認刪除區域 (如果勾選才出現)
                    if is_checked:
                        with st.container():
                            col_ask, col_yes = st.columns([3, 1], vertical_alignment="center")
                            col_ask.error("刪除此筆？")
                            if col_yes.button("是", key=f"btn_del_{record_id}", type="primary"):
                                delete_record(record_id)
                    
                    st.markdown("<hr style='margin: 4px 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
            
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
    with st.container():
        st.button("🔙 返回首頁", on_click=go_to_home, use_container_width=True)
        
    st.title("➕ 新增消費")
    
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
                # [新增] 儲存時生成唯一 ID
                new_data = pd.DataFrame({
                    "ID": [str(uuid.uuid4())],
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