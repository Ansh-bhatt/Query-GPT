import os
import sqlite3
import re
from typing import Tuple, Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = "nf_buildathon.db"

try:
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
except ImportError:
    pass


def validate_sql(sql_query_str: str) -> Tuple[bool, str]:
    """Strict security validation for read-only SQL queries"""
    sql = sql_query_str.strip()
    if not sql.upper().startswith(("SELECT ", "WITH ")):
        return False, "Query must start with SELECT or WITH"
    
    BLACKLIST = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
    for keyword in BLACKLIST:
        if re.search(r'\b' + keyword + r'\b', sql.upper()):
            return False, f"Security violation: Forbidden keyword '{keyword}' found"
    return True, "Valid read-only query"


def _local_rule_based(prompt: str) -> Tuple[str, str, str]:
    p = prompt.lower().strip()
    
    if "sect" in p or "shia" in p or "sunni" in p or "maslak" in p:
        sql = "SELECT sect AS 'Sect Group', COUNT(*) AS 'Total Users' FROM users GROUP BY sect ORDER BY COUNT(*) DESC"
        explanation = "[Local ⚡] Fetching total user count grouped by sectarian fields (Sunni, Shia, etc.)."
        return sql, explanation, "success"
        
    elif "gender" in p or "ratio" in p or "larke" in p or "larki" in p or "boys" in p or "girls" in p:
        sql = "SELECT gender AS 'Gender', COUNT(*) AS 'Count' FROM users GROUP BY gender"
        explanation = "[Local ⚡] Calculating total male (larke) vs female (larki) account breakdown across the database."
        return sql, explanation, "success"
        
    elif "kamai" in p or "revenue" in p or "payment" in p or "paisa" in p or "amount" in p:
        if "upi" in p:
            sql = "SELECT method AS 'Payment Method', SUM(amount_inr) AS 'Total Earnings (INR)' FROM payments WHERE status='success' AND LOWER(method)='upi' GROUP BY method"
            explanation = "[Local ⚡] Summing up total platform income collected via successful UPI transaction payloads."
        else:
            sql = "SELECT method AS 'Payment Method', SUM(amount_inr) AS 'Total Earnings (INR)' FROM payments WHERE status='success' GROUP BY method ORDER BY [Total Earnings (INR)] DESC"
            explanation = "[Local ⚡] Displaying premium revenue distribution across all active gateway checkout methods."
        return sql, explanation, "success"
        
    elif "ticket" in p or "csat" in p or "support" in p or "complaint" in p:
        sql = "SELECT category AS 'Ticket Category', COUNT(*) AS 'Total Tickets', ROUND(AVG(csat_score), 2) AS 'Average CSAT' FROM support_tickets GROUP BY category"
        explanation = "[Local ⚡] Analyzing customer service support logs with corresponding user CSAT feedback metrics."
        return sql, explanation, "success"
        
    elif "completeness" in p or "photo" in p or "stats" in p or "average profile" in p:
        sql = "SELECT photo_count AS 'Photos Uploaded', COUNT(*) AS 'Profiles Count', ROUND(AVG(profile_completeness_pct), 1) AS 'Avg Progress %' FROM profiles GROUP BY photo_count"
        explanation = "[Local ⚡] Analyzing relationship boundaries between user photo upload choices and profile completion ratios."
        return sql, explanation, "success"
        
    elif "delhi" in p:
        if "170" in p or "height" in p:
            sql = "SELECT u.full_name AS 'Name', u.city AS 'City', p.height_cm AS 'Height (cm)', u.profession AS 'Profession' FROM users u JOIN profiles p ON u.user_id = p.user_id WHERE LOWER(u.city)='delhi' AND p.height_cm > 170 ORDER BY p.height_cm DESC"
            explanation = "[Local ⚡] Filtering users residing in Delhi with matching height profiles exceeding 170 cm."
        else:
            sql = "SELECT profession AS 'Profession', COUNT(*) AS 'Count' FROM users WHERE LOWER(city)='delhi' GROUP BY profession ORDER BY Count DESC LIMIT 15"
            explanation = "[Local ⚡] Displaying primary occupational roles of registered platform users located in Delhi."
        return sql, explanation, "success"

    sql = "SELECT city AS 'City Location', COUNT(*) AS 'Registered Profiles' FROM users GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10"
    explanation = "[Local ⚡] Default Fallback: Displaying aggregate regional volume metrics for top active match cities."
    return sql, explanation, "success"


def generate_sql(prompt: str, use_gemini: bool = True) -> Tuple[Optional[str], Optional[str], str]:
    if not use_gemini:
        return _local_rule_based(prompt)
    
    try:
        if 'genai' not in globals() or not os.environ.get("GEMINI_API_KEY"):
            return _local_rule_based(prompt)
        
        system_prompt = """You are a SQLite expert for a Muslim matrimony platform. Convert natural language (English or Hinglish) to a single valid SQLite SELECT query.

SCHEMA:
users(user_id, full_name, gender[Male/Female], dob, phone, email, city, state, sect[Sunni/Shia/Other/Prefer not to say], mother_tongue, education_level, profession, annual_income_inr, marital_status, managed_by, is_verified[0/1], account_status[active/deactivated/suspended], created_at, last_active_at)
profiles(profile_id, user_id, bio, height_cm, photo_count, profile_completeness_pct)
partner_preferences(user_id, min_age, max_age, preferred_sect, min_education, preferred_cities)
plans(plan_id, plan_name, price_inr, duration_days, contact_credits)
subscriptions(subscription_id, user_id, plan_id, start_date, end_date, status[active/expired/cancelled], auto_renew)
payments(payment_id, user_id, subscription_id, amount_inr, method[UPI/Card/NetBanking/Wallet], status[success/failed/refunded], created_at)
interests(interest_id, sender_id, receiver_id, sent_at, status[pending/accepted/declined], responded_at)
matches(match_id, user_a_id, user_b_id, matched_at, source_interest_id)
messages(message_id, match_id, sender_id, sent_at, is_read[0/1])
profile_views(view_id, viewer_id, viewed_id, viewed_at)
reports(report_id, reporter_id, reported_id, reason, created_at, status[open/actioned/dismissed], resolved_at)
support_tickets(ticket_id, user_id, category[payment/refund/profile_edit/verification/abuse/other], created_at, status[open/resolved/closed], resolved_at, csat_score[1-5 NULL])

HINGLISH MAPPINGS:
- kamai/paisa/revenue → payments table, SUM(amount_inr)
- larke/boys → gender='Male', larki/girls → gender='Female'
- kitne log → COUNT(*) users
- active hain → account_status='active'
- sect/maslak → sect column in users
- Delhi ke → city='Delhi'

RULES:
- Return ONLY the raw SQL query, no markdown, no explanation, no backticks
- Only SELECT statements allowed
- Use meaningful column aliases with AS
- Always add ORDER BY and LIMIT 20 where appropriate"""

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt
        )
        
        response = model.generate_content(prompt)
        raw_response = response.text.strip()
        
        cleaned_sql = raw_response
        cleaned_sql = cleaned_sql.replace("```sql", "").replace("```", "").strip()
        cleaned_sql = cleaned_sql.split(";")[0].strip()
        
        is_valid, _ = validate_sql(cleaned_sql)
        if not is_valid:
            return _local_rule_based(prompt)
        
        explanation = f"[Gemini 2.5 ✨] Generated natural language to SQL query for: {prompt[:50]}..."
        return cleaned_sql, explanation, "success"
        
    except Exception as e:
        print(f"Gemini error (falling back): {str(e)}")
        return _local_rule_based(prompt)


def execute_query(sql_query_str: str) -> Tuple[Optional[List[Dict]], Optional[str]]:
    is_valid, validation_msg = validate_sql(sql_query_str)
    if not is_valid:
        return None, validation_msg
    
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query_str)
        results = cursor.fetchall()
        return [dict(row) for row in results], None
    except Exception as e:
        return None, str(e)
    finally:
        if conn:
            conn.close()
