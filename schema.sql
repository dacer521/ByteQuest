CREATE TABLE user (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  profile_pic TEXT NOT NULL
);

CREATE TABLE user_progress (
  user_id TEXT NOT NULL,
  unit INTEGER NOT NULL,
  lessons_read TEXT NOT NULL DEFAULT '[]',
  practice_completed INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, unit),
  FOREIGN KEY (user_id) REFERENCES user (id)
);
