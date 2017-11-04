
CREATE TABLE IF NOT EXISTS names
(
    name VARCHAR(128) PRIMARY KEY,
    rate DOUBLE DEFAULT 0.0 NOT NULL
);

CREATE TABLE IF NOT EXISTS votes
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL,
    email VARCHAR(256) NOT NULL UNIQUE,
    vote_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    token VARCHAR(64) NOT NULL,
    validate_date DATETIME,
    FOREIGN KEY (name) REFERENCES names(id)
);


-- CREATE INDEX index_token ON votes(token);
-- CREATE INDEX index_validate_date ON votes(validate_date);

INSERT INTO names (name) VALUES ('GeeKay'), ('GraKi'), ('GieneK'), ('GoKou'), ('GeyKee'), ('GeoKey');
