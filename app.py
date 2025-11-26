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
# 1. 隱藏輸入框提示
# 2. 隱藏數字 +/- 號
# 3. 嘗試禁用日期輸入框的鍵盤 (Mobile Friendly)
st.markdown("""
<style>
/* 基本樣式調整 */
div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
.block-container { padding-top: 4rem; }

/* 隱藏數字輸入框的箭頭 */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type=number] { -moz-appearance: textfield; }

/* 讓 Segmented Control (按鈕列) 在手機上更好按 */
div[data-testid="stSegmentedControl"] button {
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# 注入 JS 來設定日期輸入框為 "不可打字" (嘗試防止鍵盤彈出)
# 注意：這在某些瀏覽器或 Streamlit Cloud 的安全性限制下可能會有不同表現
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

# ==========================================
#  頁面 A: 首頁
# ==========================================
def show_home_page():
    df = load_data()
    
    col_header, col_btn = st.columns([8, 2])
    with col_header:
        st.subheader("我的記帳本")
    with col_btn:
        if st.button("➕ 新增一筆", use_container_width=True, type="primary"):
            go_to_add()

    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"])
        
        # --- 儀表板 ---
        total_cash = df[df["類型"] == "現金"]["金額"].sum()
        total_card = df[df["類型"] == "信用卡"]["金額"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("💵 現金總支出", f"${total_cash:,.0f}")
        m2.metric("💳 信用卡總支出", f"${total_card:,.0f}")

        st.divider()

        # --- 過濾器 (改用按鈕式) ---
        st.write("📊 篩選條件")
        
        # 月份選擇 (因為月份很多，維持下拉選單比較合適，或者可以用 Slider，但下拉最精準)
        available_months = df["日期"].dt.to_period("M").unique().astype(str)
        # 為了美觀，將月份選擇和類型選擇分開
        
        selected_month = st.selectbox("選擇月份", options=["所有時間"] + sorted(available_months, reverse=True))
        
        # [更新點] 顯示類型：改用 Segmented Control (按鈕列)
        # selection_mode="multi" 讓使用者可以複選
        selected_type = st.segmented_control(
            "顯示帳戶類型",
            options=["現金", "信用卡"],
            default=["現金", "信用卡"],
            selection_mode="multi"
        )

        # --- 應用過濾 ---
        df_filtered = df.copy()
        
        if selected_month != "所有時間":
            df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]
        
        if not selected_type:
            df_filtered = pd.DataFrame(columns=df.columns)
        else:
            df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]

        # --- 列表與刪除 ---
        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values(by="日期", ascending=False)
            df_display = df_filtered.copy()
            df_display["日期"] = df_display["日期"].dt.strftime("%Y-%m-%d")
            df_display.insert(0, "刪除", False)

            # 手機上列表標題如果太擠，可以用 caption 提示
            st.caption("勾選以刪除紀錄")
            
            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "刪除": st.column_config.CheckboxColumn("刪", width="small"),
                    "日期": st.column_config.TextColumn("日期", width="medium"),
                    "項目": st.column_config.TextColumn("項目", width="large"),
                    "類型": st.column_config.TextColumn("類型", width="small"),
                    "金額": st.column_config.NumberColumn("金額", format="$%d"),
                    "備註": st.column_config.TextColumn("備註", default="")
                },
                disabled=["日期", "項目", "類型", "金額", "備註"]
            )

            if edited_df["刪除"].any():
                to_delete_indices = edited_df[edited_df["刪除"]].index.tolist()
                if st.button(f"🗑️ 確認刪除 ({len(to_delete_indices)} 筆)", type="secondary", use_container_width=True):
                    df_new = df.drop(to_delete_indices)
                    save_data(df_new)
                    st.success("刪除成功！")
                    st.rerun()
        else:
            if not selected_type:
                st.warning("⚠️ 請至少點選一種帳戶類型 (現金/信用卡)")
            else:
                st.info("📭 查無資料")
    else:
        st.info("目前沒有紀錄，點擊右上角新增！")

# ==========================================
#  頁面 B: 新增消費
# ==========================================
def show_add_page():
    st.button("⬅️ 返回首頁", on_click=go_to_home)
    st.title("➕ 新增消費")
    
    with st.form("add_form", clear_on_submit=True):
        date = st.date_input("日期", datetime.now())
        
        # [更新點] 支付方式：改用 Segmented Control (按鈕列)
        # 比 Radio 更像 App 的切換按鈕
        category = st.segmented_control(
            "支付方式", 
            options=["現金", "信用卡"],
            default="現金",
            selection_mode="single"
        )
        
        item = st.text_input("項目", placeholder="例如: 早餐")
        
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="輸入金額")
        
        note = st.text_area("備註 (選填)", height=80)
        
        submitted = st.form_submit_button("💾 儲存並返回", type="primary", use_container_width=True)

        if submitted:
            # 檢查 category 是否為 None (雖然有 default，但預防萬一)
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