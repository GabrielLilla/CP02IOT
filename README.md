# 🏋️ Smart Gym — Sistema de Treino Inteligente

Sistema que identifica alunos via cartão RFID, registra acessos em banco de dados e acompanha os movimentos durante o treino usando visão computacional e interface gráfica.

## 🎥 Demonstração

🔗 [Assista ao vídeo de demonstração](https://youtube.com/shorts/nIlWluPvjMQ)

## 📋 Descrição

O Smart Gym combina um leitor RFID (Arduino + MFRC522) com rastreamento de pose em tempo real (Python + MediaPipe), persistência de dados (SQLite) e painel visual (Tkinter) para:

- Identificar o aluno ao aproximar o cartão RFID do leitor
- Validar o UID no banco de dados e registrar automaticamente o horário de acesso
- Detectar e contar repetições de agachamento usando a câmera
- Exibir o ângulo do joelho em tempo real em um gráfico
- Mostrar um painel com boas-vindas, contador de repetições e status da estação

## 🗂️ Estrutura do Projeto

```
smart-gym/
├── smart_gym.ino              # Código do Arduino (leitura RFID)
├── smart_gym_cp2.py           # Código Python principal (CP2)
├── populate_db.py             # Script de cadastro inicial dos alunos
├── smart_gym.db               # Banco de dados SQLite (gerado automaticamente)
├── pose_landmarker_full.task  # Modelo do MediaPipe (ver instruções abaixo)
└── README.md
```

## 🗄️ Banco de Dados (SQLite)

O arquivo `smart_gym.db` é criado automaticamente ao executar o sistema. Ele contém duas tabelas:

### Tabela `alunos`

Armazena o cadastro dos alunos da estação.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Chave primária, autoincremento |
| `nome` | TEXT | Nome do aluno |
| `uid` | TEXT | UID do cartão RFID (único) |
| `exercicio` | TEXT | Exercício prescrito |
| `objetivo` | INTEGER | Meta de repetições |

### Tabela `logs_acesso`

Registra cada sessão de treino realizada.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER | Chave primária, autoincremento |
| `aluno_id` | INTEGER | Referência ao aluno (FK) |
| `horario` | TEXT | Data e hora do acesso (`YYYY-MM-DD HH:MM:SS`) |
| `reps_total` | INTEGER | Total de repetições realizadas na sessão |

## 🔧 Hardware Necessário

| Componente | Quantidade |
|---|---|
| Arduino Uno (ou compatível) | 1 |
| Módulo RFID MFRC522 | 1 |
| Cartões/Tags RFID 13,56 MHz | 1+ |
| Câmera USB ou webcam integrada | 1 |
| Cabo USB (Arduino → PC) | 1 |

### Conexão Arduino ↔ MFRC522

| MFRC522 | Arduino Uno |
|---|---|
| SDA | Pino 10 |
| SCK | Pino 13 |
| MOSI | Pino 11 |
| MISO | Pino 12 |
| RST | Pino 9 |
| GND | GND |
| 3.3V | **3.3V** ⚠️ |

> [!WARNING]
> **O módulo MFRC522 opera em 3.3V. Conectá-lo ao pino de 5V do Arduino danifica permanentemente o leitor.** Verifique duas vezes antes de ligar — os pinos `3.3V` e `5V` ficam lado a lado no Arduino e são fáceis de confundir.

### Diagrama de Montagem

![Diagrama de conexão Arduino + MFRC522](https://github.com/user-attachments/assets/f9a8e382-b770-40c8-b203-27395fc86f11)

## 💻 Dependências

### Arduino

Instale as bibliotecas pelo **Arduino IDE → Ferramentas → Gerenciar Bibliotecas**:

- `MFRC522` (por GithubCommunity)
- `SPI` (já incluída no Arduino IDE)

### Python

Versão recomendada: **Python 3.10 ou superior**

```bash
pip install opencv-python mediapipe numpy matplotlib pyserial
```

> Os módulos `sqlite3` e `tkinter` já vêm incluídos na instalação padrão do Python — não é necessário instalá-los.

### Modelo MediaPipe

Baixe o arquivo `pose_landmarker_full.task` no link abaixo e coloque na **mesma pasta** que o `smart_gym_cp2.py`:

🔗 [Download pose_landmarker_full.task](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task)

## 🚀 Como Executar

### 1. Carregar o código no Arduino

1. Abra o arquivo `smart_gym.ino` no Arduino IDE
2. Conecte o Arduino via USB
3. Selecione a porta correta em **Ferramentas → Porta**
4. Clique em **Upload**

### 2. Descobrir a porta serial

Após o upload, anote a porta do Arduino (ex: `COM3`, `COM5` no Windows; `/dev/ttyUSB0` no Linux/Mac).

### 3. Configurar a porta no código Python

Abra o `smart_gym_cp2.py` e altere a constante no topo do arquivo:

```python
SERIAL_PORT = 'COM5'   # ← altere para a sua porta
```

### 4. Cadastrar os alunos no banco

Abra o arquivo `populate_db.py` e edite a lista `ALUNOS` com os dados reais do grupo:

```python
ALUNOS = [
    ("Nome", "XX XX XX XX", "Agachamento", 10),
    #         ↑ UID do cartão — descoberto pelo Monitor Serial do Arduino
]
```

Em seguida, execute o script uma única vez:

```bash
python populate_db.py
```

> Para descobrir o UID do seu cartão: com o código do Arduino carregado, abra o **Monitor Serial** (9600 baud) e aproxime o cartão — o UID aparecerá no formato `XX XX XX XX`.

### 5. Executar o sistema

```bash
python smart_gym_cp2.py
```

Duas janelas abrirão simultaneamente: o **painel Tkinter** e a **janela de vídeo** com o esqueleto de pose.

## 🎮 Uso

| Ação | Resultado |
|---|---|
| Aproximar cartão cadastrado ao leitor | Identifica o aluno no banco e inicia o treino |
| Pressionar `S` na janela de vídeo | Inicia como Convidado (sem Arduino) |
| Pressionar `Q` na janela de vídeo | Encerra o programa |
| Agachar (ângulo < 90°) e levantar (ângulo > 160°) | Conta 1 repetição |
| Atingir a meta de repetições | Registra o log no banco e volta para aguardar |

### Estados do sistema

```
AGUARDANDO_ID → TREINO_EM_CURSO → TREINO_CONCLUIDO → AGUARDANDO_ID
```

### Painel Tkinter

| Estado | Cor do status | Informações exibidas |
|---|---|---|
| Aguardando Login | 🟡 Amarelo | Nenhuma — aguarda cartão |
| Treino Ativo | 🟢 Verde | Nome do aluno, exercício, reps / meta |
| Treino Concluído | 🩷 Rosa | Celebração — log salvo no banco |

## ⚠️ Solução de Problemas

**Arduino não conecta**
- Verifique se a porta em `SERIAL_PORT` corresponde à porta real do dispositivo
- Certifique-se de que o Monitor Serial do Arduino IDE está **fechado** antes de rodar o Python — apenas um programa pode usar a porta serial por vez

**Câmera não abre**
- Verifique se outra aplicação está usando a câmera
- Troque o índice: `cv2.VideoCapture(0)` → `cv2.VideoCapture(1)`

**Erro ao carregar o modelo MediaPipe**
- Confirme que o arquivo `pose_landmarker_full.task` está na **mesma pasta** que o `smart_gym_cp2.py`

**Cartão não reconhecido**
- Abra o Monitor Serial do Arduino IDE para ver o UID sendo lido
- Copie o UID exatamente como aparece e adicione via `populate_db.py`

**Interface Tkinter não abre**
- Verifique se o Python foi instalado com suporte a Tkinter (no Linux: `sudo apt install python3-tk`)

## 👥 Integrantes do Grupo

- Gabriel Terra Lilla dos Santos — RM554575
- Fernando Navajas Moraes — RM555080
- Wesley Cardoso — RM557927
- José Guilherme Sipaúba Costa — RM557274
- Bruna da Costa Candeias — RM558938

## 📚 Tecnologias Utilizadas

- [MediaPipe](https://mediapipe.dev/) — Detecção de pose humana
- [OpenCV](https://opencv.org/) — Captura e processamento de vídeo
- [Tkinter](https://docs.python.org/3/library/tkinter.html) — Interface gráfica do painel da estação
- [SQLite](https://www.sqlite.org/) — Banco de dados local para cadastro e log de acessos
- [MFRC522](https://github.com/miguelbalboa/rfid) — Biblioteca RFID para Arduino
- [PySerial](https://pyserial.readthedocs.io/) — Comunicação serial Python ↔ Arduino
- [Matplotlib](https://matplotlib.org/) — Gráfico de ângulo em tempo real
