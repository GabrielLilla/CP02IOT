import cv2
import time
import threading
import sqlite3
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime
import serial
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

# ---------------------------------------------------------------
#  CONFIGURAÇÕES
# ---------------------------------------------------------------
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

DB_PATH        = 'smart_gym.db'
MODEL_PATH     = 'pose_landmarker_full.task'
SERIAL_PORT    = 'COM5'   # ← Altere para a sua porta
SERIAL_BAUD    = 9600

# ---------------------------------------------------------------
#  1. BANCO DE DADOS (SQLite)
# ---------------------------------------------------------------

def init_db():
    """Cria as tabelas se ainda não existirem e insere alunos de exemplo."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL,
            uid       TEXT    NOT NULL UNIQUE,
            exercicio TEXT    NOT NULL,
            objetivo  INTEGER NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS logs_acesso (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id   INTEGER NOT NULL,
            horario    TEXT    NOT NULL,
            reps_total INTEGER DEFAULT 0,
            FOREIGN KEY (aluno_id) REFERENCES alunos(id)
        )
    ''')

    # Insere alunos de exemplo (ignora se UID já existir)
    alunos_iniciais = [
        ("Lucas",  "2A 63 4C 73", "Agachamento", 5),
        ("Maria",  "43 B6 49 05", "Agachamento", 8),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO alunos (nome, uid, exercicio, objetivo) VALUES (?,?,?,?)",
        alunos_iniciais
    )

    con.commit()
    con.close()


def buscar_aluno(uid: str) -> dict | None:
    """Retorna o perfil do aluno pelo UID do cartão, ou None se não cadastrado."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "SELECT id, nome, exercicio, objetivo FROM alunos WHERE uid = ?", (uid,)
    )
    row = cur.fetchone()
    con.close()
    if row:
        return {"db_id": row[0], "nome": row[1], "exercicio": row[2], "objetivo": row[3]}
    return None


def registrar_log(aluno_id: int, reps: int):
    """Registra o horário de acesso e total de repetições no banco."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO logs_acesso (aluno_id, horario, reps_total) VALUES (?, ?, ?)",
        (aluno_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reps)
    )
    con.commit()
    con.close()


# ---------------------------------------------------------------
#  2. ESTADO GLOBAL COMPARTILHADO (thread-safe via Lock)
# ---------------------------------------------------------------

class AppState:
    def __init__(self):
        self.lock           = threading.Lock()
        self.estado         = "AGUARDANDO_ID"   # AGUARDANDO_ID | TREINO_EM_CURSO | TREINO_CONCLUIDO
        self.perfil         = None
        self.contador_reps  = 0
        self.estagio        = ""
        self.historico_ang  = []
        self.frame_atual    = None              # frame BGR para exibir na janela OpenCV
        self.encerrar       = False

state = AppState()

# ---------------------------------------------------------------
#  3. MEDIAPIPE
# ---------------------------------------------------------------

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options      = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO
)
detector = vision.PoseLandmarker.create_from_options(options)

fig    = plt.figure(figsize=(7, 2.5), dpi=100)
ax     = fig.add_subplot(111)
ax.set_facecolor('black')
fig.set_facecolor('black')
canvas = FigureCanvas(fig)


def calcular_angulo(a, b, c):
    a, b, c   = np.array(a), np.array(b), np.array(c)
    radianos  = (np.arctan2(c[1]-b[1], c[0]-b[0])
                 - np.arctan2(a[1]-b[1], a[0]-b[0]))
    angulo    = np.abs(radianos * 180.0 / np.pi)
    if angulo > 180.0:
        angulo = 360 - angulo
    return angulo


# ---------------------------------------------------------------
#  4. THREAD DE CAPTURA / VISÃO COMPUTACIONAL
# ---------------------------------------------------------------

serial_buffer = ""

def ler_id_serial(ser) -> str | None:
    global serial_buffer
    if ser is None or ser.in_waiting == 0:
        return None
    serial_buffer += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    if '\n' in serial_buffer:
        linha, serial_buffer = serial_buffer.split('\n', 1)
        id_lido = linha.strip().upper()
        return id_lido if id_lido else None
    return None


def thread_visao():
    """Loop principal de captura e processamento de pose (roda em thread separada)."""

    # Tenta conectar ao Arduino
    ser = None
    arduino_ok = False
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1)
        time.sleep(2)
        arduino_ok = True
        print("Arduino + MFRC522 ON")
    except Exception as e:
        print(f"Arduino OFF ({e}) — use a tecla 'S' para continuar como Convidado.")

    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        with state.lock:
            if state.encerrar:
                break

        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        tecla   = cv2.waitKey(1) & 0xFF

        with state.lock:
            est = state.estado

        # --------------------------------------------------
        #  AGUARDANDO_ID
        # --------------------------------------------------
        if est == "AGUARDANDO_ID":
            if arduino_ok:
                uid = ler_id_serial(ser)
                if uid:
                    print(f"[RFID] UID: '{uid}'")
                    perfil = buscar_aluno(uid)
                    if perfil:
                        with state.lock:
                            state.perfil        = perfil
                            state.contador_reps = 0
                            state.estagio       = ""
                            state.historico_ang = []
                            state.estado        = "TREINO_EM_CURSO"
                        print(f"Aluno: {perfil['nome']}")
                    else:
                        print(f"Cartão '{uid}' não cadastrado.")

            if tecla == ord('s'):
                perfil_convidado = {"db_id": None, "nome": "Convidado",
                                    "exercicio": "Agachamento", "objetivo": 3}
                with state.lock:
                    state.perfil        = perfil_convidado
                    state.contador_reps = 0
                    state.estagio       = ""
                    state.historico_ang = []
                    state.estado        = "TREINO_EM_CURSO"

            msg = ("APROXIME O CARTAO AO LEITOR  ou  'S' = Convidado"
                   if arduino_ok else
                   "ARDUINO DESCONECTADO — pressione 'S' para Convidado")
            cv2.putText(frame, msg, (15, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        # --------------------------------------------------
        #  TREINO_EM_CURSO
        # --------------------------------------------------
        elif est == "TREINO_EM_CURSO":
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            resultado = detector.detect_for_video(mp_image, int(time.time() * 1000))

            if resultado.pose_landmarks:
                marcos    = resultado.pose_landmarks[0]
                quadril   = [int(marcos[23].x * w), int(marcos[23].y * h)]
                joelho    = [int(marcos[25].x * w), int(marcos[25].y * h)]
                tornozelo = [int(marcos[27].x * w), int(marcos[27].y * h)]
                angulo    = calcular_angulo(quadril, joelho, tornozelo)

                with state.lock:
                    state.historico_ang.append(angulo)
                    if len(state.historico_ang) > 50:
                        state.historico_ang.pop(0)

                    if angulo > 160:
                        state.estagio = "em_pe"
                    if angulo < 90 and state.estagio == "em_pe":
                        state.estagio       = "agachado"
                        state.contador_reps += 1

                    reps    = state.contador_reps
                    obj     = state.perfil['objetivo']
                    nome    = state.perfil['nome']
                    hist    = list(state.historico_ang)

                cv2.line(frame, tuple(quadril),   tuple(joelho),    (255,255,255), 2)
                cv2.line(frame, tuple(joelho),    tuple(tornozelo), (255,255,255), 2)
                for p in [quadril, joelho, tornozelo]:
                    cv2.circle(frame, tuple(p), 8, (0, 0, 255), -1)

                # Gráfico
                ax.clear()
                ax.plot(hist, color='#00FFFF', linewidth=2)
                ax.set_ylim(0, 180)
                ax.set_title("ANGULO DO JOELHO EM TEMPO REAL", color='white', fontsize=9)
                canvas.draw()
                graf = cv2.cvtColor(np.asarray(canvas.buffer_rgba()), cv2.COLOR_RGBA2BGR)
                graf = cv2.resize(graf, (w, 200))
                frame = np.vstack((frame, graf))

                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 50), (0,0,0), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
                cv2.putText(frame,
                            f"ALUNO: {nome}  |  REPS: {reps}/{obj}",
                            (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

                with state.lock:
                    if state.contador_reps >= state.perfil['objetivo']:
                        state.estado = "TREINO_CONCLUIDO"

        # --------------------------------------------------
        #  TREINO_CONCLUIDO
        # --------------------------------------------------
        elif est == "TREINO_CONCLUIDO":
            cv2.putText(frame, "TREINO CONCLUIDO!", (w//2 - 160, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 3)

            with state.lock:
                db_id = state.perfil.get('db_id')
                reps  = state.contador_reps

            if db_id:
                registrar_log(db_id, reps)

            cv2.imshow('Academia Inteligente', frame)
            cv2.waitKey(3000)

            with state.lock:
                state.estado = "AGUARDANDO_ID"
            continue

        with state.lock:
            state.frame_atual = frame.copy()

        cv2.imshow('Academia Inteligente', frame)

        if tecla == ord('q'):
            with state.lock:
                state.encerrar = True
            break

    cap.release()
    if ser:
        ser.close()
    cv2.destroyAllWindows()


# ---------------------------------------------------------------
#  5. INTERFACE TKINTER (roda na thread principal)
# ---------------------------------------------------------------

class SmartGymGUI:
    COR_BG       = "#0d0d0d"
    COR_CARD     = "#1a1a2e"
    COR_ACCENT   = "#e91e8c"
    COR_VERDE    = "#00e676"
    COR_AMARELO  = "#ffd600"
    COR_TEXTO    = "#ffffff"
    COR_SUBTEXTO = "#aaaaaa"

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Smart Gym — Painel da Estação")
        root.configure(bg=self.COR_BG)
        root.geometry("520x420")
        root.resizable(False, False)

        self._build_ui()
        self._atualizar()

    def _build_ui(self):
        f_titulo = tk.Frame(self.root, bg=self.COR_ACCENT, height=6)
        f_titulo.pack(fill="x")

        tk.Label(self.root, text="🏋️  SMART GYM",
                 bg=self.COR_BG, fg=self.COR_ACCENT,
                 font=("Helvetica", 22, "bold")).pack(pady=(18, 2))

        tk.Label(self.root, text="Estação Inteligente de Treino",
                 bg=self.COR_BG, fg=self.COR_SUBTEXTO,
                 font=("Helvetica", 11)).pack()

        # Card de status
        self.f_card = tk.Frame(self.root, bg=self.COR_CARD,
                               padx=30, pady=20, bd=0)
        self.f_card.pack(fill="x", padx=30, pady=20)

        self.lbl_status = tk.Label(self.f_card, text="⏳  AGUARDANDO LOGIN",
                                   bg=self.COR_CARD, fg=self.COR_AMARELO,
                                   font=("Helvetica", 14, "bold"))
        self.lbl_status.pack()

        self.lbl_boas_vindas = tk.Label(self.f_card, text="",
                                        bg=self.COR_CARD, fg=self.COR_TEXTO,
                                        font=("Helvetica", 18, "bold"))
        self.lbl_boas_vindas.pack(pady=(12, 4))

        self.lbl_exercicio = tk.Label(self.f_card, text="",
                                      bg=self.COR_CARD, fg=self.COR_SUBTEXTO,
                                      font=("Helvetica", 11))
        self.lbl_exercicio.pack()

        # Contador de reps
        self.f_reps = tk.Frame(self.root, bg=self.COR_BG)
        self.f_reps.pack()

        tk.Label(self.f_reps, text="REPETIÇÕES",
                 bg=self.COR_BG, fg=self.COR_SUBTEXTO,
                 font=("Helvetica", 10)).pack()

        self.lbl_reps = tk.Label(self.f_reps, text="— / —",
                                 bg=self.COR_BG, fg=self.COR_VERDE,
                                 font=("Helvetica", 48, "bold"))
        self.lbl_reps.pack()

        # Dica inferior
        tk.Label(self.root,
                 text="Aproxime o cartão ao leitor  |  'S' = Convidado  |  'Q' = Sair",
                 bg=self.COR_BG, fg="#555555",
                 font=("Helvetica", 9)).pack(side="bottom", pady=8)

    def _atualizar(self):
        with state.lock:
            est    = state.estado
            perfil = state.perfil
            reps   = state.contador_reps

        if est == "AGUARDANDO_ID":
            self.lbl_status.config(text="⏳  AGUARDANDO LOGIN", fg=self.COR_AMARELO)
            self.lbl_boas_vindas.config(text="")
            self.lbl_exercicio.config(text="")
            self.lbl_reps.config(text="— / —", fg=self.COR_SUBTEXTO)
            self.f_card.config(bg=self.COR_CARD)

        elif est == "TREINO_EM_CURSO" and perfil:
            self.lbl_status.config(text="✅  TREINO ATIVO", fg=self.COR_VERDE)
            self.lbl_boas_vindas.config(
                text=f"Bem-vindo, {perfil['nome']}!", fg=self.COR_TEXTO)
            self.lbl_exercicio.config(
                text=f"Exercício: {perfil['exercicio']}", fg=self.COR_SUBTEXTO)
            cor_reps = (self.COR_ACCENT
                        if reps >= perfil['objetivo'] else self.COR_VERDE)
            self.lbl_reps.config(
                text=f"{reps} / {perfil['objetivo']}", fg=cor_reps)

        elif est == "TREINO_CONCLUIDO":
            self.lbl_status.config(text="🎉  TREINO CONCLUÍDO!", fg=self.COR_ACCENT)
            self.lbl_reps.config(fg=self.COR_ACCENT)

        # Verifica encerramento
        with state.lock:
            encerrar = state.encerrar
        if encerrar:
            self.root.quit()
            return

        self.root.after(300, self._atualizar)


# ---------------------------------------------------------------
#  6. MAIN
# ---------------------------------------------------------------

if __name__ == "__main__":
    init_db()

    # Visão computacional em thread separada
    t_visao = threading.Thread(target=thread_visao, daemon=True)
    t_visao.start()

    # Tkinter na thread principal
    root = tk.Tk()
    app  = SmartGymGUI(root)
    root.mainloop()

    # Garante encerramento da thread de visão
    with state.lock:
        state.encerrar = True
    t_visao.join(timeout=3)
