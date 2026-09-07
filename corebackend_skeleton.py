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
# MOTORES DEL BACKEND
# ==========================================

class InterviewEngine(QObject):
    new_message = Signal(ChatMessage)

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._generate_mock_response)

    def process_user_input(self, text: str):
        self.new_message.emit(ChatMessage(Role.USER, text))
        self._timer.start(1500) 

    def _generate_mock_response(self):
        self._timer.stop()
        responses = [
            "Detecto un pico en tu lóbulo frontal. ¿Cómo te sientes?",
            "Patrones Beta elevados. Intenta respirar profundo.",
            "Fascinante red neuronal. ¿Recuerdas algo específico?",
            "Alta carga cognitiva detectada en la corteza prefrontal."
        ]
        self.new_message.emit(ChatMessage(Role.AI, random.choice(responses)))


class BrainMapper(QObject):
    data_updated = Signal(BrainWaveData, list) 

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.timeout.connect(self._emit_mock_data)

    def start_mapping(self):
        self._timer.start(1000)

    def _emit_mock_data(self):
        waves = BrainWaveData(
            alpha=random.uniform(8.0, 12.0),
            beta=random.uniform(13.0, 30.0),
            theta=random.uniform(4.0, 7.0),
            delta=random.uniform(0.5, 3.0)
        )
        regions = [
            BrainRegion("Lóbulo Frontal", random.uniform(0.1, 0.9)),
            BrainRegion("Lóbulo Parietal", random.uniform(0.1, 0.9)),
            BrainRegion("Lóbulo Temporal", random.uniform(0.1, 0.9)),
            BrainRegion("Lóbulo Occipital", random.uniform(0.1, 0.9))
        ]
        self.data_updated.emit(waves, regions)