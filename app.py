import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="Vibe 記帳本", page_icon="💰", layout="wide")

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
    item = st.text_input("項目 (例如: 午餐)")
    category = st.selectbox("支付方式", ["現金", "信用卡"])
    amount = st.number_input("金額", min_value=0, step=1)
    note = st.text_area("備註 (選填)")
    submitted = st.form_submit_button("💾 儲存紀錄")

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
st.title("💸 Vibe Expense Tracker")
st.markdown("### 掌握你的現金流與信用額度")

# 讀取資料
df = load_data()

if not df.empty:
    # 確保日期格式正確
    df["日期"] = pd.to_datetime(df["日期"])
    
    # --- 頂部儀表板 (Dashboard) ---
    # 計算總額 (Lifetime Total)
    total_cash = df[df["類型"] == "現金"]["金額"].sum()
    total_card = df[df["類型"] == "信用卡"]["金額"].sum()
    total_all = total_cash + total_card

    # 使用 Streamlit 的 Metric 元件展示 (美觀大方)
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 現金總支出", f"${total_cash:,.0f}")
    col2.metric("💳 信用卡總支出", f"${total_card:,.0f}")
    col3.metric("🔥 總消費", f"${total_all:,.0f}")

    st.divider() # 分隔線

    # --- 過濾器與列表區 ---
    st.subheader("📋 消費明細列表")
    
    # 建立過濾器 (放在同一行)
    f_col1, f_col2 = st.columns(2)
    
    # 1. 月份過濾
    available_months = df["日期"].dt.to_period("M").unique().astype(str)
    # 預設選取最近的月份
    selected_month = f_col1.selectbox("選擇月份", options=["所有時間"] + sorted(available_months, reverse=True))
    
    # 2. 類型過濾
    selected_type = f_col2.multiselect("顯示類型", ["現金", "信用卡"], default=["現金", "信用卡"])

    # --- 應用過濾邏輯 ---
    df_filtered = df.copy()

    # 過濾月份
    if selected_month != "所有時間":
        df_filtered = df_filtered[df_filtered["日期"].dt.to_period("M").astype(str) == selected_month]

    # 過濾類型
    if selected_type:
        df_filtered = df_filtered[df_filtered["類型"].isin(selected_type)]
    else:
        df_filtered = pd.DataFrame(columns=df.columns) # 如果什麼都沒選，就清空

    # --- 顯示資料表格 ---
    # 這裡依照日期排序顯示
    df_filtered = df_filtered.sort_values(by="日期", ascending=False)
    
    # 美化表格：把日期轉回字串比較好看，並隱藏索引
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
    st.info("目前還沒有任何紀錄，請從左側側邊欄新增第一筆消費！")