import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="記帳本", page_icon="💰", layout="wide")

# --- 初始化 Session State (用於頁面切換) ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_to_add():
    st.session_state.page = 'add'
    st.rerun()

def go_to_home():
    st.session_state.page = 'home'
    st.rerun()

# --- CSS 魔法區 ---
# 1. 隱藏輸入框右下角提示
# 2. 調整頂部間距
# 3. 隱藏數字輸入框的 +/- 按鈕 (Chrome/Safari/Edge/Firefox)
css_styles = """
<style>
div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
.block-container { padding-top: 4rem; }

/* 隱藏數字輸入框的箭頭 (Chrome, Safari, Edge, Opera) */
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
/* 隱藏數字輸入框的箭頭 (Firefox) */
input[type=number] {
  -moz-appearance: textfield;
}
</style>
"""
st.markdown(css_styles, unsafe_allow_html=True)

# --- 檔案處理 ---
DATA_FILE = "expenses.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["日期", "項目", "類型", "金額", "備註"])
    df = pd.read_csv(DATA_FILE)
    # 這裡處理空值：把 NaN 變成空字串
    if "備註" in df.columns:
        df["備註"] = df["備註"].fillna("")
    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ==========================================
#  頁面 A: 首頁 (儀表板 + 列表 + 刪除)
# ==========================================
def show_home_page():
    # 讀取資料
    df = load_data()
    
    # 標題與新增按鈕區塊
    col_header, col_btn = st.columns([8, 2])
    with col_header:
        st.subheader("我的記帳本")
    with col_btn:
        # 點擊按鈕，切換狀態到 'add'
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

        # --- 過濾器 ---
        f1, f2 = st.columns(2)
        available_months = df["日期"].dt.to_period("M").unique().astype(str)
        selected_month = f1.selectbox("選擇月份", options=["所有時間"] + sorted(available_months, reverse=True))
        selected_type = f2.multiselect("顯示類型", ["現金", "信用卡"], default=["現金", "信用卡"])

        # --- 應用過濾 ---
        df_filtered = df.copy() # 這是包含原始 index 的
        
        if selected_month != "所有時間":
            df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]
        
        if not selected_type:
            df_filtered = pd.DataFrame(columns=df.columns)
        else:
            df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]

        # --- 列表與刪除功能 ---
        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values(by="日期", ascending=False)
            
            # 準備顯示用的資料 (日期轉字串)
            df_display = df_filtered.copy()
            df_display["日期"] = df_display["日期"].dt.strftime("%Y-%m-%d")
            
            # 在最前面插入一個「刪除」勾選欄位
            df_display.insert(0, "刪除", False)

            st.caption("勾選左側框框並按下刪除按鈕即可移除紀錄")
            
            # 使用 data_editor 讓使用者可以勾選
            edited_df = st.data_editor(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "刪除": st.column_config.CheckboxColumn(
                        "刪除",
                        help="勾選以刪除此紀錄",
                        default=False,
                        width="small"
                    ),
                    "金額": st.column_config.NumberColumn(format="$%d"),
                    "備註": st.column_config.TextColumn(default="") # 確保顯示空白而非 None
                },
                disabled=["日期", "項目", "類型", "金額", "備註"] # 鎖定其他欄位不讓修改，只准改刪除欄
            )

            # 檢查是否有被勾選刪除的項目
            if edited_df["刪除"].any():
                # 找出被勾選的原始 Index (因為 edited_df 保留了原始 df 的 index)
                to_delete_indices = edited_df[edited_df["刪除"]].index.tolist()
                
                if st.button(f"🗑️ 確認刪除 ({len(to_delete_indices)} 筆)", type="secondary"):
                    # 從原始 df 中刪除
                    df_new = df.drop(to_delete_indices)
                    save_data(df_new)
                    st.success("刪除成功！")
                    st.rerun()
        else:
            if not selected_type:
                st.warning("⚠️ 請選擇顯示類型")
            else:
                st.info("📭 查無資料")

    else:
        st.info("目前沒有紀錄，點擊右上角新增！")


# ==========================================
#  頁面 B: 新增消費 (獨立頁面)
# ==========================================
def show_add_page():
    st.button("⬅️ 返回首頁", on_click=go_to_home)
    st.title("➕ 新增消費紀錄")
    
    # 使用 Form 避免跳轉
    with st.form("add_form", clear_on_submit=True):
        date = st.date_input("日期", datetime.now())
        item = st.text_input("項目")
        category = st.selectbox("支付方式", ["現金", "信用卡"])
        
        # 這裡設定 step=1 但透過 CSS 隱藏了按鈕
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="輸入金額")
        
        note = st.text_area("備註 (選填)")
        
        submitted = st.form_submit_button("💾 儲存並返回", type="primary")

        if submitted:
            if item and amount is not None and amount > 0:
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
                
                # 儲存後稍作暫停讓使用者看到成功訊息，然後跳回首頁
                # 這裡我們利用 session state 直接跳回
                st.session_state.page = 'home'
                st.rerun()
            else:
                st.error("⚠️ 請輸入項目名稱與金額")

# --- 主程式流程控制 ---
if st.session_state.page == 'home':
    show_home_page()
elif st.session_state.page == 'add':
    show_add_page()