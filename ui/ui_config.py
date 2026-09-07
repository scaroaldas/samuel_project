# ui_config.py

class NeuroColors:
    # Fondos
    VOID_BLACK = "#05070A"
    PANEL_GLASS = "#0D1117"
    SURFACE_ELEVATED = "#161B22"
    
    # Texto
    PRIMARY_TEXT = "#E6EDF3"
    SECONDARY_TEXT = "#8B949E"
    
    # Regiones Cerebrales (Neón)
    PREFRONTAL = "#00E5FF"
    AMYGDALA = "#FF3B3B"
    HIPPOCAMPUS = "#B026FF"
    MOTOR_CORTEX = "#00FF9D"
    VISUAL_CORTEX = "#FFD600"

class NeuroRegions:
    # Mapeo de IDs del neuro_engine.py a Coordenadas (X, Y) en % del SVG y Colores
    # Ajusta los porcentajes según tu SVG base
    MAP = {
        "prefrontal": {"x": 0.80, "y": 0.30, "color": NeuroColors.PREFRONTAL, "label": "Corteza Prefrontal"},
        "amygdala":   {"x": 0.50, "y": 0.55, "color": NeuroColors.AMYGDALA, "label": "Amígdala"},
        "hippocampus":{"x": 0.45, "y": 0.60, "color": NeuroColors.HIPPOCAMPUS, "label": "Hipocampo"},
        "motor":      {"x": 0.55, "y": 0.15, "color": NeuroColors.MOTOR_CORTEX, "label": "Corteza Motora"},
        "visual":     {"x": 0.15, "y": 0.45, "color": NeuroColors.VISUAL_CORTEX, "label": "Corteza Visual"}
    }

class AnimationTimings:
    TYPING_INDICATOR_MS = 300
    BRAIN_PULSE_MS = 800
    WAVE_INTERPOLATION_MS = 200
    STAT_TWEENING_MS = 500
    CHAT_SLIDE_IN_MS = 200