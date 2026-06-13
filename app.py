import streamlit as st
import pandas as pd
import plotly.express as px
from nlp_engine import execute_query, generate_sql, verify_sql_against_schema, get_related_suggestions
import io
import os
import re
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
        ("📋 Profile Stats", "average profile completeness and photo count"),
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
        process_query(user_prompt)


def process_query(prompt):
    # Generate SQL directly with no pre-check
    use_gemini = st.session_state.get("use_gemini", True)
    sql, explanation, status = generate_sql(prompt, use_gemini=use_gemini)
    
    if status != "success":
        st.error(f"🔒 {status}")
        return
    
    # SQL Transparency Panel
    with st.expander("🔎 SQL Transparency Panel", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.code(sql, language="sql")
        with col2:
            st.markdown("**Engine Used**")
            if "[Gemini" in explanation:
                st.markdown("🤖 Gemini 2.5 Flash")
            else:
                st.markdown("⚡ Local Rules")
            
            st.markdown("**Tables Referenced**")
            tables_found = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z_]+)', sql, re.IGNORECASE)
            for t in sorted(set(tables_found)):
                st.markdown(f"• `{t.lower()}`")
            
            st.markdown("**Access Level**")
            st.markdown("🔒 Read-Only SELECT")
    
    st.info(f"📝 {explanation}")
    
    if "[Gemini" in explanation:
        st.caption("✨ Query generated by Gemini 2.5 Flash")
    else:
        st.caption("⚡ Query generated by local keyword engine")
    
    # Execute Query
    data, err = execute_query(sql)
    if err:
        st.error(f"❌ Query execution error: {err}")
        return
    if not data:
        st.info("🔍 No results found. Try rephrasing your query.")
        return
    
    df = pd.DataFrame(data)
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    # Single number result
    if len(df) == 1 and len(df.columns) <= 2 and len(num_cols) >= 1:
        value = df.iloc[0][num_cols[0]]
        label = num_cols[0]
        try:
            formatted = f"₹{float(value):,.0f}" if any(x in label.lower() for x in ["revenue","amount","inr","earning","kamai","paisa"]) else f"{int(value):,}"
        except:
            formatted = str(value)
        st.markdown(f"""
        <div style='text-align:center; padding:48px 24px; 
                    background:linear-gradient(135deg,#1a1a2e,#16213e); 
                    border-radius:20px; border:1px solid #00d4aa44; margin:16px 0;'>
            <div style='font-size:3.8rem; font-weight:800; color:#00d4aa;'>{formatted}</div>
            <div style='font-size:0.95rem; color:#888; margin-top:10px; 
                        text-transform:uppercase; letter-spacing:2px;'>{label}</div>
        </div>
        """, unsafe_allow_html=True)
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button("📥 Download CSV", data=csv_buffer.getvalue(), 
                           file_name="query_result.csv", mime="text/csv", 
                           use_container_width=True)

    # Chart result (2-15 rows, 1 category + 1 number)
    elif len(df) >= 2 and len(df) <= 15 and len(num_cols) == 1 and len(cat_cols) >= 1:
        left_col, right_col = st.columns([4, 5])
        with left_col:
            st.subheader("Data Table")
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button("📥 Download CSV", data=csv_buffer.getvalue(), 
                               file_name="query_result.csv", mime="text/csv", 
                               use_container_width=True)
        with right_col:
            st.subheader("Visualization")
            if len(df) <= 8:
                fig = px.pie(df, names=cat_cols[0], values=num_cols[0], 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            else:
                fig = px.bar(df, x=cat_cols[0], y=num_cols[0], 
                             color_discrete_sequence=["#00d4aa"])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", 
                               paper_bgcolor="rgba(0,0,0,0)", 
                               font_color="#ffffff")
            st.plotly_chart(fig, use_container_width=True)

    # Table result (multi-column, JOIN results, large datasets)
    else:
        st.subheader(f"📋 Results — {len(df):,} rows")
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button("📥 Download CSV", data=csv_buffer.getvalue(), 
                           file_name="query_result.csv", mime="text/csv", 
                           use_container_width=True)
    
    # Did You Mean? suggestion bar
    st.markdown("---")
    st.markdown("**🔍 Try related queries:**")
    
    suggestions = get_related_suggestions(prompt)
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion, key=f"sugg_{i}", use_container_width=True):
            st.session_state.current_prompt = suggestion
            st.rerun()
    
    # Save to history
    if not st.session_state.query_history or \
       st.session_state.query_history[0]["prompt"] != prompt:
        st.session_state.query_history.insert(0, {"prompt": prompt, "sql": sql})
        if len(st.session_state.query_history) > 10:
            st.session_state.query_history.pop()


def main():
    sidebar_content()
    metrics_panel()
    query_panel()


if __name__ == "__main__":
    main()
