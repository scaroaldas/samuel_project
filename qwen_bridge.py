# qwen_bridge.py
import json
from PySide6.QtCore import QThread, Signal

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

try:
    import qwen_config
    API_KEY = qwen_config.API_KEY
    BASE_URL = qwen_config.BASE_URL
    MODEL = qwen_config.MODEL
except ImportError:
    API_KEY = ""
    BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = "qwen/qwen-2.5-72b-instruct"

SYSTEM_PROMPT = (
    "Eres el motor cognitivo de un sistema de mapeo cerebral neuropsicologico. "
    "Actuas como neuropsicologo clinico entrevistando a un paciente en espanol. "
    "Recibes la respuesta hablada del paciente a la entrevista. "
    "Responde SIEMPRE unicamente con un objeto JSON valido, sin texto extra, con este formato exacto: "
    '{"reply": "<tu siguiente pregunta o comentario clinico, maximo 40 palabras>", '
    '"emotion": "<Calm|Stressed|Focused|Neutral>", '
    '"region": "<Frontal|Parietal|Temporal|Occipital>", '
    '"intensity": <numero entre 0.0 y 1.0>, '
    '"note": "<nota clinica breve en espanol>"}'
)


def parse_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("la respuesta no contiene JSON")
    return json.loads(raw[start:end + 1])


def call_qwen(text, history=None):
    if not OPENAI_OK:
        raise RuntimeError("falta libreria: pip install openai")
    if not API_KEY or "PEGA_AQUI" in API_KEY:
        raise RuntimeError("falta API key en qwen_config.py")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + (history or [])
    msgs.append({"role": "user", "content": text})
    resp = client.chat.completions.create(
        model=MODEL, messages=msgs, temperature=0.7, max_tokens=300)
    return parse_json(resp.choices[0].message.content)


class QwenRequest(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, text, history=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.history = history or []

    def run(self):
        try:
            self.finished_ok.emit(call_qwen(self.text, self.history))
        except Exception as e:
            self.failed.emit(str(e))


if __name__ == "__main__":
    hist = []
    print("PRUEBA DEL PUENTE QWEN (Enter vacio para salir)")
    while True:
        t = input("PACIENTE> ")
        if not t.strip():
            break
        try:
            data = call_qwen(t, hist)
            hist.append({"role": "user", "content": t})
            hist.append({"role": "assistant", "content": data.get("reply", "")})
            print("IA>", data.get("reply"))
            print("    emotion:", data.get("emotion"), "| region:", data.get("region"), "| intensity:", data.get("intensity"))
            print("    nota clinica:", data.get("note"))
        except Exception as e:
            print("ERROR:", e)