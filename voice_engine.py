# voice_engine.py
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    sr = None
    SR_AVAILABLE = False

from PySide6.QtCore import QThread, Signal


class VoiceCaptureWorker(QThread):
    transcript_ready = Signal(str)
    listening_started = Signal()
    listening_stopped = Signal()
    error = Signal(str)

    def __init__(self, language="es-ES", parent=None):
        super().__init__(parent)
        self.language = language
        self._active = False
        self._recognizer = None
        self._mic = None

    def toggle_listening(self):
        if self._active:
            self.stop_listening()
        else:
            self.start_listening()

    def start_listening(self):
        if self.isRunning():
            return
        self._active = True
        self.start()

    def stop_listening(self):
        self._active = False
        if not self.isRunning():
            self.listening_stopped.emit()

    def run(self):
        self.listening_started.emit()

        if not SR_AVAILABLE:
            self.error.emit("Falta libreria de voz: pip install SpeechRecognition PyAudio")
            self.listening_stopped.emit()
            return

        try:
            if self._recognizer is None:
                self._recognizer = sr.Recognizer()
                self._recognizer.pause_threshold = 0.8
            if self._mic is None:
                self._mic = sr.Microphone()

            with self._mic as source:
                self._recognizer.energy_threshold = 150
                while self._active:
                    try:
                        audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=15)
                    except sr.WaitTimeoutError:
                        continue
                    if not self._active:
                        break
                    try:
                        text = self._recognizer.recognize_google(audio, language=self.language)
                        if text and text.strip():
                            self.transcript_ready.emit(text.strip())
                            self._active = False
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as e:
                        self.error.emit(f"Error de reconocimiento: {e}")
                        self._active = False
        except Exception as e:
            self.error.emit(f"Error de microfono: {e}")

        self.listening_stopped.emit()