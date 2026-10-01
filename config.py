"""
Configurare globală pentru asistentul AI de coding.
Optimizat pentru RTX 3060 12GB + qwen2.5-coder:14b.
"""

# Modelul folosit prin Ollama
MODEL = "qwen2.5-coder:14b"

# Thinking mode: qwen2.5-coder NU are thinking mode -> lasă False
THINKING = False

# Câte iterații de tool-calling permite agentul într-un singur răspuns
MAX_ITERATIONS = 10

# Temperatura: 0.2 = cod determinist, mai puține halucinații
TEMPERATURE = 0.2

# Dimensiunea contextului (tokeni). Pe 12GB VRAM ține 8192.
# Dacă ai OOM (out of memory), scazi la 6144 sau 4096.
NUM_CTX = 8192

# Câți tokeni poate genera modelul per răspuns
NUM_PREDICT = 2048

# Câte layere pune pe GPU. 99 = toate.
NUM_GPU = 99

# Setări de sampling pentru cod
TOP_P = 0.9
TOP_K = 40
REPEAT_PENALTY = 1.05
NUM_BATCH = 512

# Folderul în care agentul are voie să scrie/citească
WORKSPACE_DIR = "./workspace"
