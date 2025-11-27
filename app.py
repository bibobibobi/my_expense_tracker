import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import uuid
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 設定頁面資訊 ---
st.set_page_config(page_title="雲端記帳本", page_icon="☁️", layout="wide")

# --- Google Sheets 連線 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"⚠️ 連線失敗：請檢查 Secrets 設定。")
    st.stop()

# --- CSS 優化 ---
st.markdown("""
<style>
/* 1. 修復頂部遮擋 */
.block-container { 
    padding-top: 4rem; 
    padding-bottom: 8rem; /* 底部留多一點空間給刪除按鈕 */
}

/* 隱藏不需要的提示 */
div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
input::-webkit-outer-spin-button, input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type=number] { -moz-appearance: textfield; }

/* 2. 列表格式強制單行優化 */
/* 讓文字垂直置中，並限制高度避免換行 */
div[data-testid="column"] {
    display: flex;
    align-items: center;
    height: 100%;
}

/* 日期標題 */
.date-header { 
    font-weight: bold; 
    background: #eef2f8; 
    padding: 8px 12px; 
    border-radius: 6px; 
    margin: 25px 0 10px 0;
    color: #444;
    border-left: 5px solid #ff4b4b; /* 加個紅色飾條比較明顯 */
}

/* 調整 Checkbox 垂直置中 */
div[data-testid="stCheckbox"] { 
    justify-content: center;
}
div[data-testid="stCheckbox"] label {
    min-height: 0px; /* 修正 Streamlit 預設高度導致的跑版 */
}
</style>
""", unsafe_allow_html=True)

# JS 優化: 自動跳轉與鍵盤控制
components.html("""
<script>
    function setupInteractions() {
        const doc = window.parent.document;
        
        // 1. 防止日期鍵盤跳出
        const dateInputs = doc.querySelectorAll('div[data-testid="stDateInput"] input');
        dateInputs.forEach(input => {
            input.setAttribute('inputmode', 'none'); 
            input.setAttribute('autocomplete', 'off');
        });

        // 2. [需求1] 項目輸入完 -> 自動跳金額
        const itemInput = doc.querySelector('input[aria-label="項目"]');
        const amountInput = doc.querySelector('input[aria-label="金額"]');

        if (itemInput && amountInput && !itemInput.dataset.enterBound) {
            itemInput.addEventListener('keydown', (e) => {
                // 偵測 Enter 鍵 (電腦) 或 Go/Next 鍵 (手機虛擬鍵盤代碼通常也是 13)
                if (e.key === 'Enter' || e.keyCode === 13) {
                    e.preventDefault(); 
                    amountInput.focus(); 
                }
            });
            itemInput.dataset.enterBound = 'true';
        }
    }
    setInterval(setupInteractions, 1000);
</script>
""", height=0, width=0)

# --- 初始化 Session State ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# ==========================================
#  資料庫操作
# ==========================================
def load_data():
    try:
        df = conn.read(ttl=5)
    except Exception:
        return pd.DataFrame(columns=["ID", "日期", "項目", "類型", "金額", "備註"])
        
    if df.empty:
        return pd.DataFrame(columns=["ID", "日期", "項目", "類型", "金額", "備註"])
    
    required_cols = ["ID", "日期", "項目", "類型", "金額", "備註"]
    for col in required_cols:
        if col not in df.columns: df[col] = ""
    
    if df["ID"].isnull().any():
        df.loc[df["ID"].isnull(), "ID"] = [str(uuid.uuid4()) for _ in range(df["ID"].isnull().sum())]
    
    df["備註"] = df["備註"].fillna("")
    return df

def save_new_record(new_record_df):
    try:
        full_df = conn.read(ttl=0)
    except Exception:
        full_df = pd.DataFrame(columns=["ID", "日期", "項目", "類型", "金額", "備註"])

    required_cols = ["ID", "日期", "項目", "類型", "金額", "備註"]
    for col in required_cols:
        if col not in full_df.columns: full_df[col] = ""

    updated_df = pd.concat([full_df, new_record_df], ignore_index=True)
    conn.update(data=updated_df)

# [需求2] 批量刪除功能
def delete_multiple_records(id_list):
    if not id_list:
        return
    full_df = conn.read(ttl=0)
    # 篩選掉 ID 在 id_list 裡面的資料
    full_df = full_df[~full_df["ID"].isin(id_list)]
    conn.update(data=full_df)
    st.toast(f"已刪除 {len(id_list)} 筆紀錄", icon="🗑️")
    st.rerun()

# ==========================================
#  頁面 A: 首頁
# ==========================================
def show_home_page():
    col_header, col_btn = st.columns([7, 3], vertical_alignment="center")
    with col_header:
        df = load_data() 
        st.subheader("我的記帳本") 
    with col_btn:
        if st.button("➕ 新增", use_container_width=True, type="primary"):
            st.session_state.page = 'add'
            st.rerun()

    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"])
        
        # [需求3] 預設選取當月
        all_months = sorted(df["日期"].dt.to_period("M").astype(str).unique(), reverse=True)
        current_month_str = datetime.now().strftime("%Y-%m")
        
        # 判斷預設索引：如果當月有在資料裡，就預設選它，否則選最新的
        default_index = 0
        if current_month_str in all_months:
            default_index = all_months.index(current_month_str) + 1 # +1 是因為第一個選項是 "所有時間"
        
        c_m, c_filter_ph = st.columns([1.2, 0.8]) 
        with c_m:
            sel_month = st.selectbox(
                "月份", 
                ["所有時間"] + all_months, 
                index=default_index, # 設定預設值
                label_visibility="collapsed"
            )
        
        # 資料篩選
        df_show = df.copy()
        if sel_month != "所有時間":
            df_show = df_show[df_show["日期"].dt.to_period("M").astype(str) == sel_month]
            
        # [需求3] 顯示帶有月份標題的總額
        display_title = f"{sel_month} 消費總覽" if sel_month != "所有時間" else "總消費總覽"
        st.caption(display_title) # 小標題提示目前區間
        
        cash = df_show[df_show["類型"]=="現金"]["金額"].sum()
        card = df_show[df_show["類型"]=="信用卡"]["金額"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("現金", f"${cash:,.0f}")
        m2.metric("信用卡", f"${card:,.0f}")
        
        st.divider()

        # 顯示類型過濾 (移到列表上方)
        selected_type = st.segmented_control(
            "過濾類型",
            options=["現金", "信用卡"],
            default=["現金", "信用卡"],
            selection_mode="multi",
            label_visibility="collapsed"
        )
        
        if not selected_type:
            df_show = pd.DataFrame(columns=df.columns)
        else:
            df_show = df_show[df_show["類型"].isin(selected_type)]
        
        # 列表顯示
        if not df_show.empty:
            df_show = df_show.sort_values(by="日期", ascending=False)
            dates = df_show["日期"].dt.strftime("%Y-%m-%d").unique()
            
            st.write("") 

            # [需求2] 使用 Form 來做批量刪除
            # 將整個列表包在一個 Form 裡，這樣勾選不會一直重整，按最後的按鈕才會送出
            with st.form("batch_delete_form", clear_on_submit=True):
                
                # 收集要刪除的 ID
                ids_to_delete = []

                for d in dates:
                    d_obj = datetime.strptime(d, "%Y-%m-%d")
                    w_str = ["週一","週二","週三","週四","週五","週六","週日"][d_obj.weekday()]
                    st.markdown(f'<div class="date-header">{d} ({w_str})</div>', unsafe_allow_html=True)
                    
                    day_data = df_show[df_show["日期"].dt.strftime("%Y-%m-%d") == d]
                    
                    for _, row in day_data.iterrows():
                        # [需求4] 強制單行排版
                        # 比例分配：圖示(1.2) | 項目(4.3) | 金額(2.5) | 勾選框(1)
                        c_icon, c_item, c_amt, c_chk = st.columns([1.2, 4.3, 2.5, 1], vertical_alignment="center")
                        
                        with c_icon:
                            st.write("💵" if row['類型'] == "現金" else "💳")
                        
                        with c_item:
                            # 項目名稱 (如果有備註，顯示在同一格但換行，保持排版整齊)
                            item_text = f"**{row['項目']}**"
                            if row['備註']:
                                item_text += f"<br><span style='color:grey;font-size:0.8rem'>{row['備註']}</span>"
                            st.markdown(item_text, unsafe_allow_html=True)
                            
                        with c_amt:
                            st.markdown(f"**${row['金額']:,}**")
                            
                        with c_chk:
                            # 收集勾選狀態
                            if st.checkbox("刪", key=f"del_{row['ID']}", label_visibility="collapsed"):
                                ids_to_delete.append(row['ID'])
                        
                        st.markdown("<hr style='margin: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

                st.write("")
                st.write("")
                # 批量刪除按鈕
                if st.form_submit_button("🗑️ 刪除選取項目", type="primary", use_container_width=True):
                    if ids_to_delete:
                        delete_multiple_records(ids_to_delete)
                    else:
                        st.warning("請先勾選要刪除的項目")
        else:
             st.info("📭 此區間無資料")
    else:
        st.info("目前沒有紀錄，點擊右上角新增！")

# ==========================================
#  頁面 B: 新增
# ==========================================
def show_add_page():
    with st.container():
        if st.button("🔙 取消", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
            
    st.title("➕ 新增消費")
    
    with st.form("add"):
        date = st.date_input("日期", datetime.now())
        cat = st.segmented_control("方式", ["現金", "信用卡"], default="現金")
        # [需求1] JS 會抓取這個 aria-label="項目"
        item = st.text_input("項目", placeholder="例如: 午餐") 
        # [需求1] JS 會抓取這個 aria-label="金額"
        amt = st.number_input("金額", min_value=1, value=None)
        note = st.text_area("備註")
        
        if st.form_submit_button("💾 儲存", type="primary", use_container_width=True):
            if not cat or not item or not amt:
                st.error("請填寫完整")
            else:
                new_df = pd.DataFrame([{
                    "ID": str(uuid.uuid4()),
                    "日期": date.strftime("%Y-%m-%d"),
                    "項目": item,
                    "類型": cat,
                    "金額": amt,
                    "備註": note
                }])
                save_new_record(new_df)
                st.toast("已儲存！")
                st.session_state.page = 'home'
                st.rerun()

# --- 主程式 ---
if st.session_state.page == 'home':
    show_home_page()
else:
    show_add_page()