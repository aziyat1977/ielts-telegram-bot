-- sql/01_initial.sql  ─── initial DB schema
------------------------------------------------

-- users: keeps XP, streak, premium flag, timestamps
CREATE TABLE IF NOT EXISTS users (
    id          BIGINT PRIMARY KEY,
    username    TEXT,
    xp          INTEGER     DEFAULT 0,
    streak      INTEGER     DEFAULT 0,
    is_premium  BOOLEAN     DEFAULT FALSE,
    last_seen   TIMESTAMPTZ,
    last_scored TIMESTAMPTZ
);

-- submissions: stores each essay / speaking score
CREATE TABLE IF NOT EXISTS submissions (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id),
    kind        TEXT,        -- essay | speaking
    type        TEXT,        -- reserved for future use
    band        INT,
    tips        JSONB,
    word_count  INT,
    seconds     INT,
    created_at  TIMESTAMPTZ  DEFAULT now()
);
