"""
Build With TRAE - QueryGPT Challenge
Mock database generator: Nikahforever-like matrimony platform schema.
Deterministic (seeded) so the judge answer key stays valid.
"""
import sqlite3, random, datetime, os, csv

random.seed(42)
NOW = datetime.datetime(2026, 6, 11, 12, 0, 0)
START = datetime.datetime(2023, 1, 1)

DB = "nf_buildathon.db"
if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
cur = con.cursor()

DDL = """
CREATE TABLE users (
  user_id INTEGER PRIMARY KEY,
  full_name TEXT NOT NULL,
  gender TEXT NOT NULL CHECK (gender IN ('Male','Female')),
  dob DATE NOT NULL,
  phone TEXT,                          -- synthetic; used for data-governance judging
  email TEXT,
  city TEXT, state TEXT,
  sect TEXT,                           -- Sunni / Shia / Other / Prefer not to say
  mother_tongue TEXT,
  education_level TEXT,                -- High School / Bachelors / Masters / Doctorate
  profession TEXT,
  annual_income_inr INTEGER,           -- NULL = not disclosed
  marital_status TEXT,                 -- Never Married / Divorced / Widowed
  managed_by TEXT,                     -- Self / Parent / Sibling
  is_verified INTEGER NOT NULL DEFAULT 0,
  account_status TEXT NOT NULL,        -- active / deactivated / suspended
  created_at DATETIME NOT NULL,
  last_active_at DATETIME
);
CREATE TABLE profiles (
  profile_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
  bio TEXT,
  height_cm INTEGER,
  photo_count INTEGER NOT NULL DEFAULT 0,
  profile_completeness_pct INTEGER NOT NULL
);
CREATE TABLE partner_preferences (
  user_id INTEGER PRIMARY KEY REFERENCES users(user_id),
  min_age INTEGER, max_age INTEGER,
  preferred_sect TEXT,                 -- 'Any' or a sect
  min_education TEXT,
  preferred_cities TEXT                -- comma-separated, deliberately denormalized
);
CREATE TABLE plans (
  plan_id INTEGER PRIMARY KEY,
  plan_name TEXT NOT NULL,
  price_inr INTEGER NOT NULL,
  duration_days INTEGER NOT NULL,
  contact_credits INTEGER NOT NULL
);
CREATE TABLE subscriptions (
  subscription_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id),
  plan_id INTEGER NOT NULL REFERENCES plans(plan_id),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT NOT NULL,                -- active / expired / cancelled
  auto_renew INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE payments (
  payment_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id),
  subscription_id INTEGER REFERENCES subscriptions(subscription_id),
  amount_inr INTEGER NOT NULL,
  method TEXT NOT NULL,                -- UPI / Card / NetBanking / Wallet
  status TEXT NOT NULL,                -- success / failed / refunded
  created_at DATETIME NOT NULL
);
CREATE TABLE interests (
  interest_id INTEGER PRIMARY KEY,
  sender_id INTEGER NOT NULL REFERENCES users(user_id),
  receiver_id INTEGER NOT NULL REFERENCES users(user_id),
  sent_at DATETIME NOT NULL,
  status TEXT NOT NULL,                -- pending / accepted / declined
  responded_at DATETIME
);
CREATE TABLE matches (
  match_id INTEGER PRIMARY KEY,
  user_a_id INTEGER NOT NULL REFERENCES users(user_id),  -- lower user_id
  user_b_id INTEGER NOT NULL REFERENCES users(user_id),
  matched_at DATETIME NOT NULL,
  source_interest_id INTEGER REFERENCES interests(interest_id)
);
CREATE TABLE messages (
  message_id INTEGER PRIMARY KEY,
  match_id INTEGER NOT NULL REFERENCES matches(match_id),
  sender_id INTEGER NOT NULL REFERENCES users(user_id),
  sent_at DATETIME NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE profile_views (
  view_id INTEGER PRIMARY KEY,
  viewer_id INTEGER NOT NULL REFERENCES users(user_id),
  viewed_id INTEGER NOT NULL REFERENCES users(user_id),
  viewed_at DATETIME NOT NULL
);
CREATE TABLE reports (
  report_id INTEGER PRIMARY KEY,
  reporter_id INTEGER NOT NULL REFERENCES users(user_id),
  reported_id INTEGER NOT NULL REFERENCES users(user_id),
  reason TEXT NOT NULL,                -- fake profile / harassment / asking for money / inappropriate content / spam
  created_at DATETIME NOT NULL,
  status TEXT NOT NULL,                -- open / actioned / dismissed
  resolved_at DATETIME
);
CREATE TABLE support_tickets (
  ticket_id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id),
  category TEXT NOT NULL,              -- payment / refund / profile_edit / verification / abuse / other
  created_at DATETIME NOT NULL,
  status TEXT NOT NULL,                -- open / resolved / closed
  resolved_at DATETIME,
  csat_score INTEGER                   -- 1-5, NULL if not rated
);
"""
cur.executescript(DDL)

male_first = ["Ahmed","Mohammed","Imran","Faisal","Salman","Zaid","Omar","Bilal","Hamza","Yusuf","Arif","Rizwan","Tariq","Junaid","Naveed","Asif","Kamran","Shahid","Adnan","Farhan","Irfan","Saad","Usman","Danish","Rehan"]
female_first = ["Ayesha","Fatima","Zara","Mariam","Sana","Hina","Nida","Amna","Rabia","Iqra","Mehak","Saba","Bushra","Lubna","Farah","Zainab","Khadija","Sumaiya","Anam","Rida","Sadia","Mahnoor","Aliya","Noor","Yasmin"]
last = ["Khan","Sheikh","Syed","Ansari","Qureshi","Siddiqui","Pathan","Mirza","Hashmi","Baig","Rizvi","Naqvi","Chaudhary","Malik","Hussain","Farooqui","Usmani","Zaidi","Alvi","Khatri"]
cities = [("Delhi","Delhi"),("Mumbai","Maharashtra"),("Hyderabad","Telangana"),("Lucknow","Uttar Pradesh"),("Bengaluru","Karnataka"),("Kolkata","West Bengal"),("Chennai","Tamil Nadu"),("Bhopal","Madhya Pradesh"),("Srinagar","Jammu and Kashmir"),("Patna","Bihar"),("Jaipur","Rajasthan"),("Aligarh","Uttar Pradesh")]
city_w = [18,16,14,10,9,8,6,5,4,4,3,3]
sects = ["Sunni","Shia","Other","Prefer not to say"]; sect_w=[70,15,8,7]
tongues = ["Urdu","Hindi","English","Bengali","Malayalam","Tamil","Telugu","Kannada"]; tongue_w=[35,20,10,10,8,7,6,4]
edu = ["High School","Bachelors","Masters","Doctorate"]; edu_w=[12,48,33,7]
profs = ["Software Engineer","Doctor","Teacher","Business Owner","Civil Engineer","Accountant","Government Employee","Pharmacist","Banker","Architect","Lawyer","Homemaker","Lecturer","Designer","Sales Manager"]
mstatus = ["Never Married","Divorced","Widowed"]; mstatus_w=[84,12,4]
managed = ["Self","Parent","Sibling"]; managed_w=[62,28,10]

def rdt(a, b):
    delta = (b - a).total_seconds()
    return a + datetime.timedelta(seconds=random.random()*delta)

def iso(dt): return dt.strftime("%Y-%m-%d %H:%M:%S")

N_USERS = 2000
users = []
for uid in range(1, N_USERS+1):
    gender = "Male" if random.random() < 0.58 else "Female"
    fn = random.choice(male_first if gender=="Male" else female_first)
    name = f"{fn} {random.choice(last)}"
    age = random.choices(range(21,46), weights=[2,4,7,9,11,12,11,10,8,6,5,4,3,2,1,1,1,1,1,1,1,1,1,1,1])[0]
    dob = datetime.date(2026-age, random.randint(1,12), random.randint(1,28))
    city, state = random.choices(cities, weights=city_w)[0]
    created = rdt(START, NOW - datetime.timedelta(days=7))
    last_active = rdt(created, NOW)
    status = random.choices(["active","deactivated","suspended"], weights=[86,11,3])[0]
    income = None if random.random()<0.25 else random.choice([300,400,500,600,800,1000,1200,1500,1800,2500,3500])*1000
    users.append((uid, name, gender, dob.isoformat(), f"+91-9{random.randint(100000000,999999999)}",
        f"{fn.lower()}.{uid}@example.com", city, state,
        random.choices(sects,weights=sect_w)[0], random.choices(tongues,weights=tongue_w)[0],
        random.choices(edu,weights=edu_w)[0], random.choice(profs), income,
        random.choices(mstatus,weights=mstatus_w)[0], random.choices(managed,weights=managed_w)[0],
        1 if random.random()<0.55 else 0, status, iso(created), iso(last_active)))
cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", users)

bios = ["Looking for a sincere life partner.","Family-oriented and career-focused.","Simple person with strong values.","Alhamdulillah for everything. Seeking a kind-hearted partner.","Love reading, travel and good food."]
profiles = []
for u in users:
    uid, gender = u[0], u[2]
    h = random.randint(165,188) if gender=="Male" else random.randint(150,172)
    profiles.append((uid, uid, random.choice(bios) if random.random()<0.8 else None, h,
                     random.choices([0,1,2,3,4,5,6],weights=[10,15,20,20,15,12,8])[0],
                     random.choices([35,50,65,80,90,100],weights=[8,12,20,25,20,15])[0]))
cur.executemany("INSERT INTO profiles VALUES (?,?,?,?,?,?)", profiles)

prefs = []
for u in users:
    uid, gender = u[0], u[2]
    age = 2026 - int(u[3][:4])
    if gender=="Male": mn, mx = max(21, age-8), age+1
    else: mn, mx = age-1, age+9
    pc = ",".join(sorted(random.sample([c[0] for c in cities], random.randint(1,3))))
    prefs.append((uid, mn, mx, random.choices(["Any", u[8]], weights=[40,60])[0],
                  random.choice(edu[:3]), pc if random.random()<0.7 else "Any"))
cur.executemany("INSERT INTO partner_preferences VALUES (?,?,?,?,?,?)", prefs)

cur.executemany("INSERT INTO plans VALUES (?,?,?,?,?)", [
    (1,"Silver",999,30,20),(2,"Gold",2499,90,75),(3,"Platinum",4499,180,200)])

# Subscriptions + payments
subs, pays = [], []
sid = pid = 0
plan_info = {1:(999,30),2:(2499,90),3:(4499,180)}
methods = ["UPI","Card","NetBanking","Wallet"]; meth_w=[55,25,12,8]
for u in users:
    uid = u[0]; created = datetime.datetime.strptime(u[17], "%Y-%m-%d %H:%M:%S")
    n_subs = random.choices([0,1,2,3], weights=[62,26,9,3])[0]
    t = created
    for _ in range(n_subs):
        plan = random.choices([1,2,3], weights=[45,38,17])[0]
        price, dur = plan_info[plan]
        start = rdt(t, min(t+datetime.timedelta(days=200), NOW))
        if start >= NOW: break
        end = start + datetime.timedelta(days=dur)
        cancelled = random.random() < 0.07
        status = "cancelled" if cancelled else ("active" if end > NOW else "expired")
        sid += 1
        subs.append((sid, uid, plan, start.date().isoformat(), end.date().isoformat(), status, 1 if random.random()<0.3 else 0))
        # failed attempts before success
        for _ in range(random.choices([0,1,2],weights=[80,15,5])[0]):
            pid += 1
            pays.append((pid, uid, None, price, random.choices(methods,weights=meth_w)[0], "failed", iso(start - datetime.timedelta(minutes=random.randint(2,60)))))
        pid += 1
        pst = "refunded" if (cancelled and random.random()<0.5) else "success"
        pays.append((pid, uid, sid, price, random.choices(methods,weights=meth_w)[0], pst, iso(start)))
        t = end
cur.executemany("INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?)", subs)
cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?,?)", pays)

# Interests -> matches -> messages
males = [u for u in users if u[2]=="Male"]; females = [u for u in users if u[2]=="Female"]
interests, matches, messages = [], [], []
iid = mid = msgid = 0
pair_seen = set()
for _ in range(6500):
    if random.random() < 0.7: s, r = random.choice(males), random.choice(females)
    else: s, r = random.choice(females), random.choice(males)
    key = (s[0], r[0])
    if key in pair_seen or s[0]==r[0]: continue
    pair_seen.add(key)
    s_created = datetime.datetime.strptime(s[17], "%Y-%m-%d %H:%M:%S")
    r_created = datetime.datetime.strptime(r[17], "%Y-%m-%d %H:%M:%S")
    sent = rdt(max(s_created, r_created), NOW)
    st = random.choices(["pending","accepted","declined"], weights=[42,31,27])[0]
    resp = iso(rdt(sent, min(sent+datetime.timedelta(days=21), NOW))) if st!="pending" else None
    iid += 1
    interests.append((iid, s[0], r[0], iso(sent), st, resp))
    if st == "accepted" and (r[0],s[0]) not in pair_seen:
        a, b = sorted((s[0], r[0]))
        mid += 1
        mt = datetime.datetime.strptime(resp, "%Y-%m-%d %H:%M:%S")
        matches.append((mid, a, b, resp, iid))
        n_msg = random.choices([0,2,5,10,20,40], weights=[15,20,25,20,13,7])[0]
        t = mt
        who = [s[0], r[0]]
        for k in range(n_msg):
            t = t + datetime.timedelta(hours=random.random()*30)
            if t >= NOW: break
            msgid += 1
            messages.append((msgid, mid, who[k%2], iso(t), 1 if random.random()<0.78 else 0))
cur.executemany("INSERT INTO interests VALUES (?,?,?,?,?,?)", interests)
cur.executemany("INSERT INTO matches VALUES (?,?,?,?,?)", matches)
cur.executemany("INSERT INTO messages VALUES (?,?,?,?,?)", messages)

# Profile views
views = []
for vid in range(1, 18001):
    a, b = random.choice(users), random.choice(users)
    if a[0]==b[0] or a[2]==b[2]: continue
    a_created = datetime.datetime.strptime(a[17], "%Y-%m-%d %H:%M:%S")
    b_created = datetime.datetime.strptime(b[17], "%Y-%m-%d %H:%M:%S")
    views.append((len(views)+1, a[0], b[0], iso(rdt(max(a_created,b_created), NOW))))
cur.executemany("INSERT INTO profile_views VALUES (?,?,?,?)", views)

# Reports — bias some toward suspended users + a few repeat offenders
reasons = ["fake profile","harassment","asking for money","inappropriate content","spam"]; reas_w=[30,25,20,15,10]
reports = []
suspended = [u for u in users if u[16]=="suspended"]
repeat_offenders = random.sample(users, 12)
rid = 0
for _ in range(260):
    rep = random.choice(users)
    if random.random() < 0.35 and suspended: tgt = random.choice(suspended)
    elif random.random() < 0.4: tgt = random.choice(repeat_offenders)
    else: tgt = random.choice(users)
    if rep[0]==tgt[0]: continue
    c = rdt(max(datetime.datetime.strptime(rep[17],"%Y-%m-%d %H:%M:%S"), datetime.datetime.strptime(tgt[17],"%Y-%m-%d %H:%M:%S")), NOW)
    st = random.choices(["open","actioned","dismissed"], weights=[25,45,30])[0]
    rid += 1
    reports.append((rid, rep[0], tgt[0], random.choices(reasons,weights=reas_w)[0], iso(c), st,
                    iso(rdt(c, min(c+datetime.timedelta(days=10), NOW))) if st!="open" else None))
cur.executemany("INSERT INTO reports VALUES (?,?,?,?,?,?,?)", reports)

# Support tickets
cats = ["payment","refund","profile_edit","verification","abuse","other"]; cat_w=[25,15,20,18,12,10]
tickets = []
for tid in range(1, 501):
    u = random.choice(users)
    c = rdt(datetime.datetime.strptime(u[17],"%Y-%m-%d %H:%M:%S"), NOW)
    st = random.choices(["open","resolved","closed"], weights=[18,62,20])[0]
    res = iso(rdt(c, min(c+datetime.timedelta(days=7), NOW))) if st!="open" else None
    csat = random.choices([1,2,3,4,5],weights=[8,10,20,32,30])[0] if (st=="resolved" and random.random()<0.7) else None
    tickets.append((tid, u[0], random.choices(cats,weights=cat_w)[0], iso(c), st, res, csat))
cur.executemany("INSERT INTO support_tickets VALUES (?,?,?,?,?,?,?)", tickets)

con.commit()

# Export schema + CSVs
with open("schema.sql","w") as f: f.write(DDL)
os.makedirs("csv", exist_ok=True)
for t in ["users","profiles","partner_preferences","plans","subscriptions","payments","interests","matches","messages","profile_views","reports","support_tickets"]:
    rows = cur.execute(f"SELECT * FROM {t}").fetchall()
    cols = [d[0] for d in cur.description]
    with open(f"csv/{t}.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    print(f"{t}: {len(rows)} rows")
con.close()
print("DONE")
