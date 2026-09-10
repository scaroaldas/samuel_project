# corebackend_skeleton.py
import random
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal, QTimer

# ==========================================
# MODELOS DE DATOS
# ==========================================

class Role(Enum):
    USER = "user"
    AI = "ai"

@dataclass
class ChatMessage:
    role: Role
    content: str

@dataclass
class BrainActivationResult:
    """Resultado del análisis cognitivo/emocional del texto."""
    dominant_region: str      # "Frontal", "Parietal", "Temporal", "Occipital"
    activation_level: float   # 0.0 a 1.0
    emotional_state: str      # "Calm", "Stressed", "Focused", "Neutral"

@dataclass
class BrainWaveData:
    alpha: float
    beta: float
    theta: float
    delta: float

@dataclass
class BrainRegion:
    name: str
    activation_level: float

# ==========================================
# MOTOR DE ENTREVISTA (Analiza el chat)
# ==========================================

class InterviewEngine(QObject):
    new_message = Signal(ChatMessage)
    brain_activation = Signal(BrainActivationResult)

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._generate_mock_response)
        self._last_text = ""

    def process_user_input(self, text: str):
        """Recibe el texto del usuario y simula el procesamiento."""
        self.new_message.emit(ChatMessage(Role.USER, text))
        self._last_text = text
        # Latencia variable según longitud del texto
        delay = max(1000, min(2500, len(text) * 50))
        self._timer.start(delay)

    def _generate_mock_response(self):
        self._timer.stop()

        # Lógica simple de análisis por palabras clave
        text = self._last_text.lower()
        region = "Frontal"
        state = "Neutral"

        if "dolor" in text or "estrés" in text or "estres" in text or "miedo" in text or "ansiedad" in text:
            region = "Temporal"
            state = "Stressed"
        elif "feliz" in text or "bien" in text or "alegre" in text or "tranquilo" in text:
            region = "Frontal"
            state = "Calm"
        elif "pienso" in text or "analizo" in text or "recuerdo" in text or "memoria" in text:
            region = "Parietal"
            state = "Focused"

        # Emitir el resultado del análisis cerebral
        result = BrainActivationResult(
            dominant_region=region,
            activation_level=random.uniform(0.75, 0.99),
            emotional_state=state
        )
        self.brain_activation.emit(result)

        # Respuesta de la IA según el estado detectado
        responses = {
            "Stressed": "Detecto tensión en tu red neural. Respira y profundicemos en eso.",
            "Calm": "Tus patrones indican un estado óptimo. Excelente conexión.",
            "Focused": "Alta actividad cognitiva detectada. Continuemos el análisis.",
            "Neutral": "Interesante. Mis sensores captan nuevos matices en tu respuesta."
        }
        self.new_message.emit(ChatMessage(Role.AI, responses.get(state, "Procesando datos...")))


# ==========================================
# MAPEADOR CEREBRAL (Telemetría continua)
# ==========================================

class BrainMapper(QObject):
    data_updated = Signal(BrainWaveData, list)

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._emit_mock_data)

    def start_mapping(self):
        """Inicia la emisión de datos biométricos simulados."""
        self._timer.start(1000)

    def _emit_mock_data(self):
        waves = BrainWaveData(
            alpha=random.uniform(8.0, 12.0),
            beta=random.uniform(13.0, 30.0),
            theta=random.uniform(4.0, 7.0),
            delta=random.uniform(0.5, 3.0)
        )
        regions = [
            BrainRegion("Lóbulo Frontal", random.uniform(0.1, 0.5)),
            BrainRegion("Lóbulo Parietal", random.uniform(0.1, 0.5)),
            BrainRegion("Lóbulo Temporal", random.uniform(0.1, 0.5)),
            BrainRegion("Lóbulo Occipital", random.uniform(0.1, 0.5))
        ]
        self.data_updated.emit(waves, regions)