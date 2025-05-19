CREATE TABLE artists(
  id   TEXT PRIMARY KEY,
  name TEXT,
  uri  TEXT,
  spotify_id TEXT
);

CREATE TABLE metrics(
  artist_id TEXT,
  source    TEXT,
  metric    TEXT,
  ts        TIMESTAMPTZ DEFAULT now(),
  val       NUMERIC,
  PRIMARY KEY (artist_id,source,metric,ts)
);