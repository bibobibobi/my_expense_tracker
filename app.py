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

# --- CSS 優化 (修復遮擋與列表格式) ---
st.markdown("""
<style>
/* 1. 修復頂部遮擋：加大頂部間距 */
.block-container { 
    padding-top: 4rem; 
    padding-bottom: 5rem;
}

/* 隱藏不需要的提示 */
div[data-testid="InputInstructions"] > span:nth-child(1) { display: none; }
input::-webkit-outer-spin-button, input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
input[type=number] { -moz-appearance: textfield; }

/* 列表文字樣式優化 */
.list-item-text { 
    font-size: 1.15rem; 
    font-weight: 600; 
    color: #333; 
    line-height: 1.4;
    display: flex;
    align-items: center;
}
.list-item-sub { 
    font-size: 0.9rem; 
    color: #666; 
    margin-left: 1.6rem; /* 讓備註稍微縮排 */
}

/* 日期標題 */
.date-header { 
    font-weight: bold; 
    background: #f0f2f6; 
    padding: 6px 12px; 
    border-radius: 6px; 
    margin: 20px 0 8px 0;
    color: #444;
}

/* 調整 Checkbox 垂直置中 */
div[data-testid="stCheckbox"] { 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    margin-top: 5px;
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
    # 優化：ttl=5 代表 5 秒內重複讀取會用快取，減少卡頓
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
        full_df = conn.read(ttl=0) # 寫入前強制讀最新的
    except Exception:
        full_df = pd.DataFrame(columns=["ID", "日期", "項目", "類型", "金額", "備註"])

    required_cols = ["ID", "日期", "項目", "類型", "金額", "備註"]
    for col in required_cols:
        if col not in full_df.columns: full_df[col] = ""

    updated_df = pd.concat([full_df, new_record_df], ignore_index=True)
    conn.update(data=updated_df)

def delete_record(record_id):
    full_df = conn.read(ttl=0)
    full_df = full_df[full_df["ID"] != record_id]
    conn.update(data=full_df)
    st.toast("已刪除", icon="🗑️")
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
        months = sorted(df["日期"].dt.to_period("M").astype(str).unique(), reverse=True)
        
        c_m, _ = st.columns([1, 1])
        with c_m:
            sel_month = st.selectbox("月份", ["所有時間"] + months, label_visibility="collapsed")
        
        df_show = df.copy()
        if sel_month != "所有時間":
            df_show = df_show[df_show["日期"].dt.to_period("M").astype(str) == sel_month]
            
        cash = df_show[df_show["類型"]=="現金"]["金額"].sum()
        card = df_show[df_show["類型"]=="信用卡"]["金額"].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("現金", f"${cash:,.0f}")
        m2.metric("信用卡", f"${card:,.0f}")
        
        st.divider()

        # [修復] 找回消失的過濾按鈕
        selected_type = st.segmented_control(
            "顯示類型",
            options=["現金", "信用卡"],
            default=["現金", "信用卡"],
            selection_mode="multi",
            label_visibility="collapsed"
        )
        
        # 應用類型過濾
        if not selected_type:
            df_show = pd.DataFrame(columns=df.columns)
        else:
            df_show = df_show[df_show["類型"].isin(selected_type)]
        
        # 列表顯示
        if not df_show.empty:
            df_show = df_show.sort_values(by="日期", ascending=False)
            dates = df_show["日期"].dt.strftime("%Y-%m-%d").unique()
            
            st.write("") # 間距

            for d in dates:
                d_obj = datetime.strptime(d, "%Y-%m-%d")
                w_str = ["週一","週二","週三","週四","週五","週六","週日"][d_obj.weekday()]
                st.markdown(f'<div class="date-header">{d} ({w_str})</div>', unsafe_allow_html=True)
                
                day_data = df_show[df_show["日期"].dt.strftime("%Y-%m-%d") == d]
                
                for _, row in day_data.iterrows():
                    # [修復] 列表排版：左邊資訊 (85%)，右邊刪除框 (15%)
                    c_txt, c_del = st.columns([6, 1], vertical_alignment="center")
                    
                    with c_txt:
                        icon = "💵" if row['類型'] == "現金" else "💳"
                        note = f"<div class='list-item-sub'>{row['備註']}</div>" if row['備註'] else ""
                        # [修復] HTML 結構優化
                        st.markdown(
                            f"""
                            <div class='list-item-text'>
                                <span style='margin-right:8px;'>{icon}</span>
                                <span style='flex-grow:1;'>{row['項目']}</span>
                                <code>${row['金額']:,}</code>
                            </div>
                            {note}
                            """, 
                            unsafe_allow_html=True
                        )
                    
                    with c_del:
                        is_checked = st.checkbox("刪", key=f"d_{row['ID']}", label_visibility="collapsed")
                    
                    # [修復] 刪除確認區域
                    if is_checked:
                        # 使用 container 讓背景稍微不同，或是直接顯示文字
                        with st.container():
                            st.markdown("<span style='color:red; font-size:0.8rem; font-weight:bold;'>確定刪除?</span>", unsafe_allow_html=True)
                            # 按鈕加大一點
                            if st.button("是", key=f"cf_{row['ID']}", type="secondary", use_container_width=True):
                                delete_record(row['ID'])
                                
                    st.markdown("<hr style='margin: 4px 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
        else:
             if selected_type:
                 st.info("📭 此區間無資料")
             else:
                 st.warning("⚠️ 請選擇至少一種類型")
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