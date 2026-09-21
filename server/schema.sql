BEGIN IMMEDIATE;
CREATE TABLE users (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, subject TEXT NOT NULL,
 name TEXT NOT NULL, UNIQUE(provider, subject)
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at REAL NOT NULL
);
CREATE TABLE clubs (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, summary TEXT NOT NULL,
 rules TEXT NOT NULL, owner_id TEXT NOT NULL REFERENCES users(id)
);
CREATE TABLE memberships (
 club_id TEXT NOT NULL REFERENCES clubs(id), user_id TEXT NOT NULL REFERENCES users(id),
 status TEXT NOT NULL CHECK(status IN ('pending','active','rejected')),
 reason TEXT NOT NULL DEFAULT '', PRIMARY KEY(club_id, user_id)
);
CREATE TABLE media (
 id TEXT PRIMARY KEY, club_id TEXT NOT NULL REFERENCES clubs(id), author_id TEXT NOT NULL REFERENCES users(id),
 data BLOB NOT NULL, content_type TEXT NOT NULL
);
CREATE TABLE posts (
 id TEXT PRIMARY KEY, club_id TEXT NOT NULL REFERENCES clubs(id), author_id TEXT NOT NULL REFERENCES users(id),
 client_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('work','knowledge','question','chat')),
 title TEXT NOT NULL, body TEXT NOT NULL, feedback TEXT NOT NULL DEFAULT '',
 media_id TEXT UNIQUE REFERENCES media(id), status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
 reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, UNIQUE(author_id, client_id)
);
CREATE INDEX posts_club_status ON posts(club_id,status,created_at DESC,id);
CREATE TABLE comments (
 id TEXT PRIMARY KEY, post_id TEXT NOT NULL REFERENCES posts(id), author_id TEXT NOT NULL REFERENCES users(id),
 body TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
 reason TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE INDEX comments_post ON comments(post_id,status,created_at,id);
CREATE TABLE events (
 id TEXT PRIMARY KEY, club_id TEXT NOT NULL REFERENCES clubs(id), title TEXT NOT NULL,
 description TEXT NOT NULL, location TEXT NOT NULL, starts_at TEXT NOT NULL, ends_at TEXT NOT NULL,
 capacity INTEGER NOT NULL CHECK(capacity > 0), status TEXT NOT NULL CHECK(status IN ('open','cancelled'))
);
CREATE TABLE registrations (
 event_id TEXT NOT NULL REFERENCES events(id), user_id TEXT NOT NULL REFERENCES users(id),
 status TEXT NOT NULL CHECK(status IN ('confirmed','waiting','cancelled')), created_at TEXT NOT NULL,
 PRIMARY KEY(event_id,user_id)
);
CREATE INDEX registration_queue ON registrations(event_id,status,created_at,user_id);
CREATE TABLE handovers (
 id TEXT PRIMARY KEY, club_id TEXT NOT NULL REFERENCES clubs(id), from_user_id TEXT NOT NULL REFERENCES users(id),
 to_user_id TEXT NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','completed','expired'))
);
CREATE UNIQUE INDEX one_pending_handover ON handovers(club_id) WHERE status='pending';
CREATE TABLE audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, club_id TEXT NOT NULL REFERENCES clubs(id),
 actor_id TEXT NOT NULL REFERENCES users(id), action TEXT NOT NULL, target_id TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
PRAGMA user_version=1;
COMMIT;
