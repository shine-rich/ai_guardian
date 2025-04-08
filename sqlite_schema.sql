CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    source TEXT,
    destination TEXT,
    resolved_hostname TEXT,
    status TEXT
);
