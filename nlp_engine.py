import os
import sqlite3
import re
import json
from typing import Tuple, Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = "nf_buildathon.db"

VALID_TABLES = {
    "users", "profiles", "partner_preferences", "plans",
    "subscriptions", "payments", "interests", "matches",
    "messages", "profile_views", "reports", "support_tickets"
}

try:
    from google import genai
    from google.genai import types
except ImportError:
    pass


def validate_sql(sql_query_str: str) -> Tuple[bool, str]:
    sql = sql_query_str.strip()
    if not sql.upper().startswith(("SELECT ", "WITH ")):
        return False, "Query must start with SELECT or WITH"
    
    BLACKLIST = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
    for keyword in BLACKLIST:
        if re.search(r'\b' + keyword + r'\b', sql.upper()):
            return False, f"Security violation: Forbidden keyword '{keyword}' found"
    return True, "Valid read-only query"


def verify_sql_against_schema(sql: str) -> Tuple[bool, str]:
    pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_]+)'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    tables = [m.lower() for m in matches]
    
    for table in tables:
        if table not in VALID_TABLES:
            return False, f"Hallucinated table: {table}"
    return True, "OK"


def get_related_suggestions(prompt: str) -> list:
    try:
        if 'genai' not in globals() or not os.environ.get("GEMINI_API_KEY"):
            return ["show gender ratio", "total revenue by method", "city wise user count"]
        
        system_prompt = """
You are a query suggestion engine for a matrimony platform database with these tables:
users, profiles, partner_preferences, plans, subscriptions, payments,
interests, matches, messages, profile_views, reports, support_tickets

Given the user's current query, suggest exactly 3 short related follow-up queries they might want to ask next. Each suggestion max 6 words.
Return ONLY a JSON array of 3 strings. No markdown. No explanation.
Example: ["gender ratio by city", "verified users count", "top professions in Mumbai"]
"""

        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0,
                max_output_tokens=500,
            )
        )
        cleaned = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(cleaned)
        if isinstance(result, list) and len(result) == 3:
            return result
        else:
            return ["show gender ratio", "total revenue by method", "city wise user count"]
        
    except Exception as e:
        print(f"Related suggestions failed: {e}")
        return ["show gender ratio", "total revenue by method", "city wise user count"]


def generate_sql(prompt: str, use_gemini: bool = True) -> Tuple[Optional[str], Optional[str], str]:
    # ALWAYS try Gemini first if enabled
    if use_gemini:
        try:
            if 'genai' in globals() and os.environ.get("GEMINI_API_KEY"):
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
reports(report_id, reporter_id, reported_id, reason[fake profile/harassment/asking for money/inappropriate content/spam], created_at, status[open/actioned/dismissed], resolved_at)
support_tickets(ticket_id, user_id, category[payment/refund/profile_edit/verification/abuse/other], created_at, status[open/resolved/closed], resolved_at, csat_score[1-5 NULL])

HINGLISH MAPPINGS:
- kamai/paisa/revenue → payments table, SUM(amount_inr)
- larke/boys → gender='Male', larki/girls → gender='Female'
- kitne log → COUNT(*) users
- active hain → account_status='active'
- sect/maslak → sect column in users
- Delhi ke → city='Delhi'

EXAMPLE QUERIES AND RESPONSES:
- "konsa city mein sabse zyada sunni users hain" → SELECT city AS 'City', COUNT(*) AS 'Sunni Users' FROM users WHERE sect='Sunni' GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10
- "Delhi mein kitne shia hain" → SELECT COUNT(*) AS 'Shia Users in Delhi' FROM users WHERE city='Delhi' AND sect='Shia'
- "sabse zyada matches kahan se hain" → SELECT u.city AS 'City', COUNT(*) AS 'Total Matches' FROM matches m JOIN users u ON m.user_a_id=u.user_id GROUP BY u.city ORDER BY COUNT(*) DESC LIMIT 10
- "konsa plan sabse popular hai" → SELECT p.plan_name AS 'Plan', COUNT(*) AS 'Subscribers' FROM subscriptions s JOIN plans p ON s.plan_id=p.plan_id GROUP BY p.plan_name ORDER BY COUNT(*) DESC

RULES:
- Return ONLY the raw SQL query, no markdown, no explanation, no backticks
- Only SELECT statements allowed
- Use meaningful column aliases with AS
- Always add ORDER BY and LIMIT 20 where appropriate"""

                client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0,
                        max_output_tokens=500,
                    )
                )
                gemini_sql = response.text.strip()
                
                if gemini_sql:
                    # Strip fences
                    gemini_sql = gemini_sql.strip()
                    gemini_sql = re.sub(r'```sql|```', '', gemini_sql).strip()
                    gemini_sql = gemini_sql.split(';')[0].strip()
                    
                    # Security check
                    is_valid, msg = validate_sql(gemini_sql)
                    if not is_valid:
                        print(f"[WARN] Gemini SQL failed validation: {msg}")
                    else:
                        # Hallucination check
                        schema_ok, schema_msg = verify_sql_against_schema(gemini_sql)
                        if not schema_ok:
                            print(f"[WARN] Gemini hallucinated: {schema_msg}")
                        else:
                            # Generate a proper explanation
                            explanation = f"[Gemini 2.5 ✨] Showing {prompt.strip().capitalize()}"
                            return gemini_sql, explanation, "success"
        
        except Exception as e:
            print(f"Gemini failed, using local fallback: {e}")
    
    # LOCAL KEYWORD FALLBACK (only runs if Gemini is off or failed)
    p = prompt.lower().strip()
    
    if "sect" in p or "shia" in p or "sunni" in p or "maslak" in p:
        sql = "SELECT sect AS 'Sect Group', COUNT(*) AS 'Total Users' FROM users GROUP BY sect ORDER BY COUNT(*) DESC"
        explanation = "[Local ⚡] Fetching total user count grouped by sectarian fields (Sunni, Shia, etc.)."
        return sql, explanation, "success"
    
    elif "gender" in p or "ratio" in p or "larke" in p or "larki" in p or "boys" in p or "girls" in p:
        sql = "SELECT gender AS 'Gender', COUNT(*) AS 'Count' FROM users GROUP BY gender"
        explanation = "[Local ⚡] Calculating total male vs female account breakdown."
        return sql, explanation, "success"
    
    elif "kamai" in p or "revenue" in p or "payment" in p or "paisa" in p or "amount" in p:
        if "upi" in p:
            sql = "SELECT method AS 'Payment Method', SUM(amount_inr) AS 'Total Earnings (INR)' FROM payments WHERE status='success' AND LOWER(method)='upi' GROUP BY method"
        else:
            sql = "SELECT method AS 'Payment Method', SUM(amount_inr) AS 'Total Earnings (INR)' FROM payments WHERE status='success' GROUP BY method ORDER BY 2 DESC"
        explanation = "[Local ⚡] Displaying revenue distribution across payment methods."
        return sql, explanation, "success"
    
    elif "ticket" in p or "csat" in p or "support" in p or "complaint" in p:
        sql = "SELECT category AS 'Ticket Category', COUNT(*) AS 'Total Tickets', ROUND(AVG(csat_score), 2) AS 'Average CSAT' FROM support_tickets GROUP BY category"
        explanation = "[Local ⚡] Analyzing support tickets with CSAT scores."
        return sql, explanation, "success"
    
    elif "completeness" in p or "photo" in p or "stats" in p or "average profile" in p:
        sql = "SELECT photo_count AS 'Photos Uploaded', COUNT(*) AS 'Profiles Count', ROUND(AVG(profile_completeness_pct), 1) AS 'Avg Progress %' FROM profiles GROUP BY photo_count"
        explanation = "[Local ⚡] Analyzing profile completeness vs photo upload stats."
        return sql, explanation, "success"
    
    elif "delhi" in p:
        if "170" in p or "height" in p:
            sql = "SELECT u.full_name AS 'Name', u.city AS 'City', p.height_cm AS 'Height (cm)', u.profession AS 'Profession' FROM users u JOIN profiles p ON u.user_id = p.user_id WHERE LOWER(u.city)='delhi' AND p.height_cm > 170 ORDER BY p.height_cm DESC"
        else:
            sql = "SELECT profession AS 'Profession', COUNT(*) AS 'Count' FROM users WHERE LOWER(city)='delhi' GROUP BY profession ORDER BY 2 DESC LIMIT 15"
        explanation = "[Local ⚡] Filtering users in Delhi."
        return sql, explanation, "success"
    
    # Default fallback
    sql = "SELECT city AS 'City Location', COUNT(*) AS 'Registered Profiles' FROM users GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10"
    explanation = "[Local ⚡] Default: Showing top cities by registered user count."
    return sql, explanation, "success"


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
