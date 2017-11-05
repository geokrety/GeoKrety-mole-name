
CREATE TABLE IF NOT EXISTS names
(
    name VARCHAR(128) PRIMARY KEY,
    rate DOUBLE DEFAULT 0.0 NOT NULL
);

CREATE TABLE IF NOT EXISTS proposed_names
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128),
    username VARCHAR(128),
    email VARCHAR(256) NOT NULL,
    create_datetime DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS votes
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL,
    new_name VARCHAR(128),
    email VARCHAR(256) NOT NULL UNIQUE,
    vote_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
    token VARCHAR(64) NOT NULL,
    validate_datetime DATETIME,
    FOREIGN KEY (name) REFERENCES names(id),
    FOREIGN KEY (new_name) REFERENCES names(id)
);


-- CREATE INDEX index_token ON votes(token);
-- CREATE INDEX index_validate_date ON votes(validate_date);

INSERT INTO names (name) VALUES ('GeeKay'), ('GraKi'), ('GieneK'), ('GoKou'), ('GeyKee'), ('GeoKey');
