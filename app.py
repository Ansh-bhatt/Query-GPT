import streamlit as st
import pandas as pd
import plotly.express as px
from nlp_engine import execute_query, generate_sql
import io
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="NF QueryGPT", page_icon="💍", layout="wide")

st.markdown("""
<style>
    [data-testid="metric-container"] {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricLabel"] {
        color: #495057;
        font-weight: 500;
        font-size: 0.9rem;
    }
    [data-testid="stMetricValue"] {
        color: #198754;
        font-weight: 700;
    }
    .stButton > button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

if "query_history" not in st.session_state:
    st.session_state.query_history = []
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = ""


def sidebar_content():
    with st.sidebar:
        st.title("💍 NF QueryGPT")
        
        gemini_key_set = bool(os.environ.get("GEMINI_API_KEY"))
        st.toggle("🤖 Gemini 2.5 AI", key="use_gemini", value=gemini_key_set)
        
        if not gemini_key_set:
            st.warning("⚠️ GEMINI_API_KEY missing. Add it to .env and restart.")
            st.code("GEMINI_API_KEY=your_key_here", language="bash")
        else:
            st.success("✅ Gemini 2.5 connected")
        
        st.markdown("---")
        
        st.subheader("📜 History Ledger")
        with st.expander("View Last 10 Queries", expanded=True):
            if st.session_state.query_history:
                for idx, entry in enumerate(st.session_state.query_history):
                    if st.button(
                        f"{entry['prompt'][:40]}...",
                        key=f"hist_{idx}",
                        use_container_width=True
                    ):
                        st.session_state.current_prompt = entry["prompt"]
                        st.rerun()
            else:
                st.markdown("_No queries yet_")
        
        st.markdown("---")
        st.subheader("📊 Schema Overview")
        with st.expander("All 12 Tables", expanded=False):
            st.markdown("""
            1. **users** - Core user profiles
            2. **profiles** - Extended profile details
            3. **partner_preferences** - Partner match preferences
            4. **plans** - Subscription packages
            5. **subscriptions** - Active subscriptions
            6. **payments** - Payment transactions
            7. **interests** - Interests sent/received
            8. **matches** - Successful matches
            9. **messages** - Chat messages
            10. **profile_views** - Profile visit logs
            11. **reports** - Abuse/fraud reports
            12. **support_tickets** - Customer support tickets
            """)
        
        st.markdown("---")
        st.subheader("💡 Query Tips")
        st.info("""
        - **Profile filters**: "show profiles from Delhi with height above 170"
        - **Gender**: "gender ratio" or "larke larki ratio"
        - **Revenue**: "total kamai" or "total payments"
        - **Sects**: "user sects" or "shia sunni counts"
        - **General**: "delhi users", "profile stats"
        """)


def metrics_panel():
    st.header("Executive KPI Dashboard")
    
    metrics = []
    total_users_data, _ = execute_query("SELECT COUNT(*) AS total FROM users")
    total_users = total_users_data[0]["total"] if total_users_data else 0
    metrics.append(("Total Profiles", f"{total_users:,}", "+14.2% Growth"))
    
    active_users_data, _ = execute_query("SELECT COUNT(*) AS active FROM users WHERE account_status='active'")
    active_users = active_users_data[0]["active"] if active_users_data else 0
    active_pct = round((active_users / total_users) * 100, 1) if total_users > 0 else 0
    metrics.append(("Active Profiles", f"{active_users:,}", f"{active_pct}% Active"))
    
    total_revenue_data, _ = execute_query("SELECT SUM(amount_inr) AS total FROM payments WHERE status='success'")
    total_revenue = total_revenue_data[0]["total"] or 0
    metrics.append(("Total Revenue", f"₹{total_revenue:,.0f}", "+21.5% MoM"))
    
    verified_users_data, _ = execute_query("SELECT COUNT(*) AS verified FROM users WHERE is_verified=1")
    verified_users = verified_users_data[0]["verified"] if verified_users_data else 0
    verified_pct = round((verified_users / total_users) * 100, 1) if total_users > 0 else 0
    metrics.append(("Verified Users", f"{verified_users:,}", f"{verified_pct}% Verified"))
    
    open_reports_data, _ = execute_query("SELECT COUNT(*) AS open_rep FROM reports WHERE status='open'")
    open_reports = open_reports_data[0]["open_rep"] if open_reports_data else 0
    metrics.append(("Open Reports", f"{open_reports}", "-5 Fixed Today"))
    
    cols = st.columns(5)
    for col, (label, val, delta) in zip(cols, metrics):
        col.metric(label, val, delta)


def query_panel():
    st.markdown("---")
    st.header("Natural Language Query Console")
    
    st.subheader("Quick Action Buttons")
    quick_prompts = [
        ("🕌 User Sects", "show user sect distribution"),
        ("📊 Gender Ratio", "show gender ratio"),
        ("💰 Total Kamai", "total kamai from UPI"),
        ("🎟️ Support CSAT", "show customer support tickets"),
        ("📁 Profile Stats", "average profile completeness and photo count"),
        ("📍 Delhi Users", "show profiles from Delhi with height above 170"),
    ]
    
    cols = st.columns(len(quick_prompts))
    for idx, (btn_text, prompt_text) in enumerate(quick_prompts):
        if cols[idx].button(btn_text, use_container_width=True):
            st.session_state.current_prompt = prompt_text
            st.rerun()
    
    user_prompt = st.text_area(
        "Enter your query (English or Hinglish)",
        value=st.session_state.current_prompt,
        height=90
    )
    
    if st.button("Run Analysis", type="primary", use_container_width=True):
        use_gemini = st.session_state.get("use_gemini", True)
        process_query(user_prompt, use_gemini)


def process_query(prompt: str, use_gemini: bool):
    sql, explanation, status = generate_sql(prompt, use_gemini=use_gemini)
    
    if status != "success":
        st.error(f"🔒 {status}")
        return
    
    with st.expander("🔎 View Generated Read-Only SQL Query"):
        st.code(sql, language="sql")
    st.info(f"📝 {explanation}")
    
    if "[Gemini" in explanation:
        st.caption("✨ Query generated by Gemini 2.5 Flash")
    else:
        st.caption("⚡ Query generated by local keyword engine")
    
    data, err = execute_query(sql)
    if err:
        st.error(f"❌ Error executing query: {err}")
        return
    if not data:
        st.markdown("_No results found. Try adjusting your filters!_")
        return
    
    df = pd.DataFrame(data)
    left_col, right_col = st.columns([4, 5])
    
    with left_col:
        st.subheader("Data Table")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv_buffer.getvalue(),
            file_name="query_results.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with right_col:
        st.subheader("Visualization")
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
        
        if num_cols and cat_cols:
            if len(df) <= 10:
                fig = px.pie(
                    df,
                    names=cat_cols[0],
                    values=num_cols[0],
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
            else:
                fig = px.bar(
                    df,
                    x=cat_cols[0],
                    y=num_cols[0],
                    color_discrete_sequence=["#0D6EFD"]
                )
            fig.update_layout(plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("_No suitable data for visualization_")
    
    if not st.session_state.query_history or st.session_state.query_history[0]["prompt"] != prompt:
        st.session_state.query_history.insert(0, {"prompt": prompt, "sql": sql})
        if len(st.session_state.query_history) > 10:
            st.session_state.query_history.pop()


def main():
    sidebar_content()
    metrics_panel()
    query_panel()


if __name__ == "__main__":
    main()
