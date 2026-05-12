import sqlite3
from datetime import datetime

DB_PATH = 'smart_gym.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS alunos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL,
    uid       TEXT    NOT NULL UNIQUE,
    exercicio TEXT    NOT NULL,
    objetivo  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS logs_acesso (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id   INTEGER NOT NULL,
    horario    TEXT    NOT NULL,
    reps_total INTEGER DEFAULT 0,
    FOREIGN KEY (aluno_id) REFERENCES alunos(id)
);
"""

ALUNOS = [
    ("Gabriel",  "C3 48 89 4F", "Agachamento", 10),
    ("Fernando", "73 1D E4 FE", "Agachamento",  8),
    ("Wesley",   "A9 F6 00 98", "Agachamento",  6),
    ("Guilherme","D6 EE 4C 1F", "Agachamento",  5),
    ("Bruna",    "55 66 77 88", "Agachamento",  7),
]

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.executescript(SCHEMA)

    inseridos  = 0
    ignorados  = 0
    for aluno in ALUNOS:
        try:
            cur.execute(
                "INSERT INTO alunos (nome, uid, exercicio, objetivo) VALUES (?,?,?,?)",
                aluno
            )
            inseridos += 1
            print(f"  ✅  Cadastrado: {aluno[0]} (UID: {aluno[1]})")
        except sqlite3.IntegrityError:
            ignorados += 1
            print(f"  ⚠️   Já existe:  {aluno[0]} (UID: {aluno[1]}) — ignorado")

    con.commit()

    # Exibe estado atual do banco
    print(f"\n{'─'*50}")
    print(f"  Banco: {DB_PATH}")
    print(f"  Inseridos: {inseridos}  |  Ignorados: {ignorados}")
    print(f"{'─'*50}")
    print(f"\n  Tabela 'alunos':")
    for row in cur.execute("SELECT id, nome, uid, exercicio, objetivo FROM alunos"):
        print(f"    [{row[0]}] {row[1]:12s} | UID: {row[2]} | {row[3]} | Meta: {row[4]} reps")

    print(f"\n  Tabela 'logs_acesso':")
    rows = cur.execute("SELECT COUNT(*) FROM logs_acesso").fetchone()[0]
    print(f"    {rows} registro(s) de acesso no banco.")

    con.close()
    print(f"\n  Banco pronto! Execute: python smart_gym_cp2.py\n")


if __name__ == "__main__":
    main()
