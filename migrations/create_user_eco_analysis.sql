-- Table pour stocker les résultats des questionnaires analyses avancées
CREATE TABLE IF NOT EXISTS user_eco_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date_filled TEXT NOT NULL,
    score INTEGER NOT NULL,
    details TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
