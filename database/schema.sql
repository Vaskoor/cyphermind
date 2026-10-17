
CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, name TEXT, created_at TIMESTAMP DEFAULT NOW());
CREATE TABLE conversations (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id) ON DELETE CASCADE, title TEXT, created_at TIMESTAMP DEFAULT NOW());
CREATE TABLE messages (id SERIAL PRIMARY KEY, conversation_id INT REFERENCES conversations(id) ON DELETE CASCADE, role TEXT NOT NULL, content TEXT NOT NULL, encrypted BOOLEAN DEFAULT false, tokens INT, created_at TIMESTAMP DEFAULT NOW());
CREATE TABLE encryption_keys (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id), public_key TEXT, private_key_enc TEXT, algorithm TEXT DEFAULT 'RSA-2048', created_at TIMESTAMP DEFAULT NOW());
CREATE TABLE api_keys (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id), key_hash TEXT UNIQUE, active BOOLEAN DEFAULT true, created_at TIMESTAMP DEFAULT NOW());
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
