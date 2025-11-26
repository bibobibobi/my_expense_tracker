import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="記帳本", page_icon="💰", layout="wide")

# --- CSS 魔法區 (修正遮擋與樣式) ---
hide_input_instructions = """
<style>
/* 隱藏輸入框右下角的提示字 */
div[data-testid="InputInstructions"] > span:nth-child(1) {
    display: none;
}
/* 修正頂部遮擋問題：
   原本設 2rem 太靠近頂部，導致手機上標題被遮住。
   現在改為 4rem (約 64px)，預留足夠空間給頂端選單。
*/
.block-container {
    padding-top: 4rem;
}
</style>
"""
st.markdown(hide_input_instructions, unsafe_allow_html=True)

# --- 檔案處理 ---
DATA_FILE = "expenses.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["日期", "項目", "類型", "金額", "備註"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 側邊欄：新增交易 (使用 Form 防止跳轉) ---
st.sidebar.header("➕ 新增一筆消費")

# 重要：所有輸入元件都在這個 form 裡面
# 這樣選擇日期時，Streamlit 就不會重新執行程式(Rerun)，也就不會跳回首頁
with st.sidebar.form("entry_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    item = st.text_input("項目")
    category = st.selectbox("支付方式", ["現金", "信用卡"])
    
    # 修改點：value=None 讓預設值為空，而不是 0
    amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="請輸入金額")
    
    note = st.text_area("備註 (選填)")
    
    # 只有按下這個按鈕，程式才會執行刷新
    submitted = st.form_submit_button("💾 儲存紀錄")

    if submitted:
        # 因為 amount 預設是 None，所以要檢查是否為 None
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
            st.toast(f"已新增: {item} ${amount}", icon='✅')
        else:
            if amount is None:
                st.error("⚠️ 請輸入金額！")
            else:
                st.error("⚠️ 請輸入項目名稱與正確金額！")

# --- 主畫面邏輯 ---

# 讀取資料
df = load_data()

if not df.empty:
    df["日期"] = pd.to_datetime(df["日期"])
    
    # --- 頂部儀表板 ---
    total_cash = df[df["類型"] == "現金"]["金額"].sum()
    total_card = df[df["類型"] == "信用卡"]["金額"].sum()
    
    col1, col2 = st.columns(2)
    col1.metric("💵 現金總支出", f"${total_cash:,.0f}")
    col2.metric("💳 信用卡總支出", f"${total_card:,.0f}")

    st.divider()

    # --- 過濾器與列表區 ---
    f_col1, f_col2 = st.columns(2)
    
    available_months = df["日期"].dt.to_period("M").unique().astype(str)
    selected_month = f_col1.selectbox("選擇月份", options=["所有時間"] + sorted(available_months, reverse=True))
    
    selected_type = f_col2.multiselect("顯示類型", ["現金", "信用卡"], default=["現金", "信用卡"])

    # --- 應用過濾邏輯 ---
    df_filtered = df.copy()

    if selected_month != "所有時間":
        df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]

    if not selected_type:
        df_filtered = pd.DataFrame(columns=df.columns)
    else:
        df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]

    # --- 顯示資料表格 ---
    if not df_filtered.empty:
        df_filtered = df_filtered.sort_values(by="日期", ascending=False)
        
        df_display = df_filtered.copy()
        df_display["日期"] = df_display["日期"].dt.strftime("%Y-%m-%d")
        
        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "金額": st.column_config.NumberColumn(format="$%d")
            }
        )
    else:
        if not selected_type:
            st.warning("⚠️ 請至少選擇一種「顯示類型」來查看列表")
        else:
            st.info("📭 這個區間沒有符合條件的紀錄")

else:
    st.info("目前還沒有任何紀錄，請從左側側邊欄新增第一筆消費！")