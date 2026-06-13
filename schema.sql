
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
