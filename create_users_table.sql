CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY,
    user_id BIGINT,
    expense int,
    description text,
    category text,
    datetime TIMESTAMP DEFAULT NOW()
);