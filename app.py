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
    st.error(f"⚠️ 連線失敗。")
    st.stop()

# --- CSS 優化 (核心修復) ---
st.markdown("""
<style>
/* 1. 頂部與底部間距 */
.block-container { 
    padding-top: 3.5rem; 
    padding-bottom: 2rem;
}

/* 隱藏提示 */
div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
input::-webkit-outer-spin-button, input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type=number] { -moz-appearance: textfield; }

/* 2. [關鍵修復] 強制手機版 Columns 不換行 */
div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important; /* 禁止換行 */
    align-items: center; /* 垂直置中 */
}

/* 讓 Column 可以縮到很小，不會被內容撐開導致換行 */
div[data-testid="column"] {
    min-width: 0px !important; 
    flex: 1 1 auto;
}

/* 3. 列表內容排版 */
.list-content {
    display: flex;
    align-items: center;
    width: 100%;
    overflow: hidden; /* 防止溢出 */
}
.list-icon {
    font-size: 1.2rem;
    margin-right: 8px;
    flex-shrink: 0;
}
.list-text-group {
    display: flex;
    flex-direction: column;
    flex-grow: 1;
    overflow: hidden;
    margin-right: 8px;
}
.list-item {
    font-weight: 600;
    color: #333;
    font-size: 1rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.list-note {
    font-size: 0.8rem;
    color: #888;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.list-amount {
    font-family: monospace;
    font-weight: bold;
    color: #333;
    font-size: 1rem;
    flex-shrink: 0; /* 金額不准縮小 */
}

/* 日期標題 */
.date-header { 
    font-weight: bold; 
    background: #f8f9fa; 
    padding: 5px 10px; 
    border-radius: 6px; 
    margin: 15px 0 5px 0;
    color: #555;
    border-left: 4px solid #ff4b4b;
    font-size: 0.95rem;
}

/* 4. 按鈕樣式極小化 */
div[data-testid="column"] button {
    padding: 0px 8px !important; /* 極小內距 */
    font-size: 0.85rem !important;
    height: 32px !important;
    min-height: 0px !important;
    margin: 0 !important;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

# JS 優化
components.html("""
<script>
    function setupInteractions() {
        const doc = window.parent.document;
        const dateInputs = doc.querySelectorAll('div[data-testid="stDateInput"] input');
        dateInputs.forEach(input => {
            input.setAttribute('inputmode', 'none'); 
            input.setAttribute('autocomplete', 'off');
        });

        const itemInput = doc.querySelector('input[aria-label="項目"]');
        const amountInput = doc.querySelector('input[aria-label="金額"]');
        if (itemInput && amountInput && !itemInput.dataset.enterBound) {
            itemInput.addEventListener('keydown', (e) => {
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
if 'delete_target' not in st.session_state:
    st.session_state.delete_target = None

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
    st.cache_data.clear()

def delete_record(record_id):
    full_df = conn.read(ttl=0)
    full_df = full_df[full_df["ID"] != record_id]
    conn.update(data=full_df)
    st.session_state.delete_target = None
    st.cache_data.clear()
    st.toast("已刪除", icon="🗑️")
    st.rerun()

def set_delete_target(record_id):
    if st.session_state.delete_target == record_id:
        st.session_state.delete_target = None
    else:
        st.session_state.delete_target = record_id

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
        
        all_months = sorted(df["日期"].dt.to_period("M").astype(str).unique(), reverse=True)
        current_month_str = datetime.now().strftime("%Y-%m")
        
        default_index = 0
        if current_month_str in all_months:
            default_index = all_months.index(current_month_str) + 1 
        
        c_m, c_dummy = st.columns([1.5, 1]) 
        with c_m:
            sel_month = st.selectbox(
                "月份", 
                ["所有時間"] + all_months, 
                index=default_index,
                label_visibility="collapsed"
            )
        
        display_title = f"{sel_month} 消費總覽" if sel_month != "所有時間" else "總消費總覽"
        st.caption(display_title)
        
        df_show = df.copy()
        if sel_month != "所有時間":
            df_show = df_show[df_show["日期"].dt.to_period("M").astype(str) == sel_month]
            
        cash = df_show[df_show["類型"]=="現金"]["金額"].sum()
        card = df_show[df_show["類型"]=="信用卡"]["金額"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("現金", f"${cash:,.0f}")
        m2.metric("信用卡", f"${card:,.0f}")
        
        st.divider()

        selected_type = st.segmented_control(
            "過濾", options=["現金", "信用卡"], default=["現金", "信用卡"],
            selection_mode="multi", label_visibility="collapsed"
        )
        
        if not selected_type:
            df_show = pd.DataFrame(columns=df.columns)
        else:
            df_show = df_show[df_show["類型"].isin(selected_type)]
        
        if not df_show.empty:
            df_show = df_show.sort_values(by="日期", ascending=False)
            dates = df_show["日期"].dt.strftime("%Y-%m-%d").unique()
            
            st.write("") 

            for d in dates:
                d_obj = datetime.strptime(d, "%Y-%m-%d")
                w_str = ["週一","週二","週三","週四","週五","週六","週日"][d_obj.weekday()]
                st.markdown(f'<div class="date-header">{d} ({w_str})</div>', unsafe_allow_html=True)
                
                day_data = df_show[df_show["日期"].dt.strftime("%Y-%m-%d") == d]
                
                for _, row in day_data.iterrows():
                    # [關鍵佈局]
                    # 左欄 (4.5) : 圖示 + 項目 + 備註 + 金額
                    # 右欄 (1) : 按鈕
                    # CSS flex-wrap: nowrap 會保證它們在同一行
                    c_content, c_btn = st.columns([4.5, 1], vertical_alignment="center")
                    
                    with c_content:
                        icon = "💵" if row['類型'] == "現金" else "💳"
                        # 處理備註
                        note_div = ""
                        if row['備註']:
                            note_div = f'<div class="list-note">{row["備註"]}</div>'
                        
                        # [修復] 乾淨的 HTML 結構，避免 </div> 錯誤
                        html_code = f"""
                        <div class="list-content">
                            <div class="list-icon">{icon}</div>
                            <div class="list-text-group">
                                <div class="list-item">{row['項目']}</div>
                                {note_div}
                            </div>
                            <div class="list-amount">${row['金額']:,}</div>
                        </div>
                        """
                        st.markdown(html_code, unsafe_allow_html=True)
                    
                    with c_btn:
                        if st.session_state.delete_target == row['ID']:
                            st.button("確定", key=f"cf_{row['ID']}", type="primary", on_click=delete_record, args=(row['ID'],), use_container_width=True)
                        else:
                            st.button("刪除", key=f"del_{row['ID']}", type="secondary", on_click=set_delete_target, args=(row['ID'],), use_container_width=True)
                    
                    st.markdown("<hr style='margin: 0; border-top: 1px solid #f0f0f0;'>", unsafe_allow_html=True)
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
        item = st.text_input("項目", placeholder="例如: 午餐")
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