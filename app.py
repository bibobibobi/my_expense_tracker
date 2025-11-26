import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="記帳本", page_icon="💰", layout="wide")

# --- CSS 魔法區 (隱藏輸入框提示字與調整樣式) ---
hide_input_instructions = """
<style>
/* 隱藏輸入框右下角的 "Press Enter to apply" 提示 */
div[data-testid="InputInstructions"] > span:nth-child(1) {
    display: none;
}
/* 微調一下頂部間距，因為標題拿掉了 */
.block-container {
    padding-top: 2rem;
}
</style>
"""
st.markdown(hide_input_instructions, unsafe_allow_html=True)

# --- 檔案處理 (自動存取 CSV) ---
DATA_FILE = "expenses.csv"

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["日期", "項目", "類型", "金額", "備註"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 側邊欄：新增交易 ---
st.sidebar.header("➕ 新增一筆消費")
with st.sidebar.form("entry_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    # 這裡的 label 已經很清楚，移除了 placeholder 避免混淆
    item = st.text_input("項目") 
    category = st.selectbox("支付方式", ["現金", "信用卡"])
    amount = st.number_input("金額", min_value=0, step=1)
    note = st.text_area("備註 (選填)")
    submitted = st.form_submit_button("儲存紀錄")

    if submitted:
        if item and amount > 0:
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
            st.error("請輸入項目名稱與金額！")

# --- 主畫面邏輯 ---
# (已移除原本的 Vibe Title 和 Slogan)

# 讀取資料
df = load_data()

if not df.empty:
    # 確保日期格式正確
    df["日期"] = pd.to_datetime(df["日期"])
    
    # --- 頂部儀表板 (Dashboard) ---
    total_cash = df[df["類型"] == "現金"]["金額"].sum()
    total_card = df[df["類型"] == "信用卡"]["金額"].sum()
    # 這裡可以保留總額顯示，若不需要也可以移除
    
    col1, col2 = st.columns(2)
    col1.metric("現金總支出", f"${total_cash:,.0f}")
    col2.metric("信用卡總支出", f"${total_card:,.0f}")

    st.divider() # 分隔線

    # --- 過濾器與列表區 ---
    
    # 建立過濾器
    f_col1, f_col2 = st.columns(2)
    
    # 1. 月份過濾
    available_months = df["日期"].dt.to_period("M").unique().astype(str)
    selected_month = f_col1.selectbox("選擇月份", options=["所有時間"] + sorted(available_months, reverse=True))
    
    # 2. 類型過濾
    selected_type = f_col2.multiselect("顯示類型", ["現金", "信用卡"], default=["現金", "信用卡"])

    # --- 應用過濾邏輯 ---
    df_filtered = df.copy()

    # 過濾月份
    if selected_month != "所有時間":
        df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]

    # 過濾類型 (修復：增加判斷是否為空)
    if not selected_type:
        # 如果使用者把類型都取消勾選，就清空資料，避免報錯
        df_filtered = pd.DataFrame(columns=df.columns)
    else:
        df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]

    # --- 顯示資料表格 ---
    # 只有當有資料要顯示時，才執行排序和格式化，避免對空資料操作報錯
    if not df_filtered.empty:
        df_filtered = df_filtered.sort_values(by="日期", ascending=False)
        
        df_display = df_filtered.copy()
        # 安全的日期格式轉換
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
        # 當過濾結果為空時顯示的提示
        if not selected_type:
            st.warning("⚠️ 請至少選擇一種「顯示類型」來查看列表")
        else:
            st.info("這個區間沒有符合條件的紀錄")

else:
    st.info("目前還沒有任何紀錄，請從左側側邊欄新增第一筆消費！")