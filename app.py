import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import uuid
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
    font-size: 1.1rem;
    font-weight: bold;
    color: #444;
    background-color: #f0f2f6;
    padding: 8px 12px;
    border-radius: 8px;
    margin-top: 20px;
    margin-bottom: 10px;
}

/* [修改] 列表項目文字放大 */
.list-item-text {
    font-size: 1.25rem; /* 加大字體 (約20px) */
    font-weight: 600;   /* 加粗 */
    line-height: 1.5;
    color: #1f1f1f;
}

/* [修改] 備註文字放大 */
.list-item-sub {
    font-size: 1rem;    /* 加大備註 (約16px) */
    color: #666;
    margin-top: 2px;
}

/* 調整 Checkbox */
div[data-testid="stCheckbox"] {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

# JS: 1. 防止日期鍵盤彈出 2. [新增] 輸入完項目後自動跳到金額
components.html("""
<script>
    // 定義一個函數來檢查並綁定事件
    function setupInteractions() {
        const doc = window.parent.document;
        
        // 1. 日期輸入框優化
        const dateInputs = doc.querySelectorAll('div[data-testid="stDateInput"] input');
        dateInputs.forEach(input => {
            input.setAttribute('inputmode', 'none'); 
            input.setAttribute('autocomplete', 'off');
        });

        // 2. 自動跳轉焦點 (項目 -> 金額)
        // 透過 aria-label 找到對應的輸入框
        const itemInput = doc.querySelector('input[aria-label="項目"]');
        const amountInput = doc.querySelector('input[aria-label="金額"]');

        if (itemInput && amountInput && !itemInput.dataset.enterBound) {
            itemInput.addEventListener('keydown', (e) => {
                // 如果按下 Enter (電腦) 或 Go/Next (手機)
                if (e.key === 'Enter' || e.keyCode === 13) {
                    e.preventDefault(); // 阻止表單預設提交
                    amountInput.focus(); // 強制跳到金額欄位
                }
            });
            // 標記已綁定，避免重複綁定
            itemInput.dataset.enterBound = 'true';
        }
    }

    // 因為 Streamlit 會動態渲染，我們設定一個定時器每秒檢查一次
    // 這樣可以確保切換頁面後功能依然有效
    setInterval(setupInteractions, 1000);
</script>
""", height=0, width=0)

# --- 檔案處理 ---
DATA_FILE = "expenses.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["ID", "日期", "項目", "類型", "金額", "備註"])
    
    df = pd.read_csv(DATA_FILE)
    if "ID" not in df.columns:
        df["ID"] = [str(uuid.uuid4()) for _ in range(len(df))]
        save_data(df)
    if "備註" in df.columns:
        df["備註"] = df["備註"].fillna("")
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def delete_record(record_id):
    df = load_data()
    df = df[df["ID"] != record_id]
    save_data(df)
    st.toast("已刪除", icon="🗑️")
    st.rerun()

# ==========================================
#  頁面 A: 首頁
# ==========================================
def show_home_page():
    df = load_data()
    
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
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                weekday_str = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][date_obj.weekday()]
                st.markdown(f'<div class="date-header">{date_str} ({weekday_str})</div>', unsafe_allow_html=True)
                
                day_records = df_filtered[df_filtered["日期"].dt.strftime("%Y-%m-%d") == date_str]
                
                for _, row in day_records.iterrows():
                    c_info, c_del = st.columns([5.5, 1], vertical_alignment="center")
                    record_id = row['ID']
                    
                    with c_info:
                        icon = "💵" if row['類型'] == "現金" else "💳"
                        note_html = f"<div class='list-item-sub'>{row['備註']}</div>" if row['備註'] else ""
                        
                        # [修改] 使用新的 class list-item-text
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
                        is_checked = st.checkbox("刪", key=f"chk_{record_id}", label_visibility="collapsed")
                    
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
        
        # [關鍵] 這裡的 label 文字必須與 JS 中的 aria-label 選擇器一致
        item = st.text_input("項目", placeholder="例如: 午餐")
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="輸入金額")
        note = st.text_area("備註 (選填)", height=60)
        
        submitted = st.form_submit_button("💾 儲存", type="primary", use_container_width=True)

        if submitted:
            if not category:
                st.error("⚠️ 請選擇支付方式")
            elif item and amount is not None and amount > 0:
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