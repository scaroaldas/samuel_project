"""
core/neuro_engine.py
Motor Cognitivo para Neural Brain Mapper.
Este módulo contiene la lógica de mapeo neurolingüístico y el modelo de datos 
para la activación cerebral teórica.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

# ==========================================
# 1. MODELO DE DATOS
# ==========================================

@dataclass
class BrainActivationResult:
    """
    Modelo de respuesta estandarizado para la activación cerebral.
    """
    region_id: str
    region_name: str
    intensity: float  # Rango normalizado de 0.0 a 1.0
    detected_emotion: str


@dataclass
class RegionProfile:
    """
    Perfil interno de cada región para la Base de Conocimiento.
    """
    name: str
    function: str
    default_emotion: str
    keywords: List[str]
    patterns: List[str]  # Para frases o patrones lingüísticos más complejos


# ==========================================
# 2. BASE DE CONOCIMIENTO NEUROCIENCIA
# ==========================================

NEURO_KNOWLEDGE_BASE: Dict[str, RegionProfile] = {
    "cpf": RegionProfile(
        name="Corteza Prefrontal",
        function="Funciones ejecutivas, lógica, planificación, toma de decisiones.",
        default_emotion="Neutral / Analítico",
        keywords=["plan", "lógica", "estrategia", "analizar", "decidir", "objetivo", "futuro", "estructurar"],
        patterns=["tengo que", "debería", "mi objetivo es", "paso a paso"]
    ),
    "amygdala": RegionProfile(
        name="Amígdala",
        function="Reactividad emocional, procesamiento de amenazas, miedo, ansiedad.",
        default_emotion="Miedo / Ansiedad",
        keywords=["miedo", "peligro", "terror", "ansiedad", "amenaza", "pánico", "angustia", "asustado"],
        patterns=["me siento amenazado", "no puedo soportarlo", "es un desastre"]
    ),
    "hippocampus": RegionProfile(
        name="Hipocampo",
        function="Recuperación de memoria episódica, coherencia narrativa, contexto.",
        default_emotion="Nostalgia / Reflexivo",
        keywords=["recuerdo", "ayer", "infancia", "olvidé", "memoria", "pasado", "experiencia", "vez"],
        patterns=["cuando era niño", "la última vez que", "me acuerdo de"]
    ),
    "temporal_cortex": RegionProfile(
        name="Corteza Temporal",
        function="Comprensión del lenguaje (Área de Wernicke), procesamiento auditivo, semántica.",
        default_emotion="Atento / Comunicativo",
        keywords=["escuchar", "sonido", "entender", "significado", "palabra", "ruido", "voz", "idioma"],
        patterns=["no te entiendo", "escucha esto", "lo que dices significa"]
    ),
    "insula": RegionProfile(
        name="Ínsula",
        function="Interocepción, emociones viscerales, asco, empatía, conciencia corporal.",
        default_emotion="Disgusto / Empático",
        keywords=["asco", "náusea", "estómago", "sentir", "cuerpo", "vísceras", "repugnante", "empatía"],
        patterns=["me revolvió el estómago", "siento en las entrañas", "me da grima"]
    ),
    "occipital_cortex": RegionProfile(
        name="Corteza Occipital",
        function="Procesamiento visual, imaginación visual, colores, formas.",
        default_emotion="Contemplativo / Visual",
        keywords=["ver", "luz", "color", "imagen", "brillante", "oscuro", "mirar", "visual"],
        patterns=["lo vi claramente", "era de color", "a primera vista"]
    )
}

# Umbral de normalización para el cálculo de intensidad en el mock.
# En la versión con IA real, esto se calculará por similitud de embeddings.
MOCK_MAX_MATCHES_THRESHOLD = 5.0 


# ==========================================
# 3. FUNCIÓN DE ANÁLISIS (MOCK)
# ==========================================

def _calculate_intensity(match_count: int) -> float:
    """
    Calcula la intensidad normalizada (0.0 a 1.0) basada en el número de coincidencias.
    """
    if match_count <= 0:
        return 0.0
    # Normalización simple: cada coincidencia suma un 20% hasta llegar al 100%
    intensity = match_count / MOCK_MAX_MATCHES_THRESHOLD
    return round(min(1.0, intensity), 2)


def analyze_response(text: str) -> BrainActivationResult:
    """
    Analiza el texto de la entrevista y devuelve la región cerebral 
    teóricamente más activada y su intensidad.
    
    NOTA: Esta es una implementación MOCK basada en coincidencia de palabras clave.
    En futuras iteraciones, la lógica interna será reemplazada por la llamada 
    a la API de IA (LLM) para análisis semántico profundo.
    
    Args:
        text (str): La respuesta en texto plano del entrevistado.
        
    Returns:
        BrainActivationResult: El resultado del mapeo cerebral.
    """
    if not text or not text.strip():
        return BrainActivationResult(
            region_id="cpf",
            region_name="Corteza Prefrontal",
            intensity=0.0,
            detected_emotion="Neutral / Analítico"
        )

    text_lower = text.lower()
    # Tokenización básica para palabras clave sueltas
    words = re.findall(r'\b\w+\b', text_lower)
    
    region_scores: Dict[str, int] = {region_id: 0 for region_id in NEURO_KNOWLEDGE_BASE}

    # 1. Búsqueda de coincidencias
    for region_id, profile in NEURO_KNOWLEDGE_BASE.items():
        score = 0
        
        # Contar palabras clave sueltas
        for keyword in profile.keywords:
            score += words.count(keyword)
            
        # Contar patrones de frases (búsqueda de subcadenas)
        for pattern in profile.patterns:
            score += text_lower.count(pattern)
            
        region_scores[region_id] = score

    # 2. Determinar la región dominante
    dominant_region_id = max(region_scores, key=region_scores.get) # type: ignore
    max_score = region_scores[dominant_region_id]
    
    # Si no hay ninguna coincidencia, devolvemos un estado base (Red por defecto / CPF basal)
    if max_score == 0:
        dominant_region_id = "cpf"
        max_score = 0

    dominant_profile = NEURO_KNOWLEDGE_BASE[dominant_region_id]

    # 3. Construir y devolver el resultado
    return BrainActivationResult(
        region_id=dominant_region_id,
        region_name=dominant_profile.name,
        intensity=_calculate_intensity(max_score),
        detected_emotion=dominant_profile.default_emotion
    )
