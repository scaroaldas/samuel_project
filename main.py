# main.py - Versión Final Integrada Qwen + Voz + Mock Fallback
import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindowFull as MainWindow
from corebackend_skeleton import InterviewEngine, BrainMapper, ChatMessage, Role, BrainActivationResult
try:
    from qwen_bridge import QwenRequest
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False

from voice_engine import VoiceCaptureWorker
from session_logger import SessionLogger


def main():
    app = QApplication(sys.argv)

    interview_engine = InterviewEngine()
    brain_mapper = BrainMapper()
    session_logger = SessionLogger()
    voice_worker = VoiceCaptureWorker(language="es-ES")
    main_window = MainWindow()

    # --- Historial de conversación para Qwen ---
    chat_history_qwen = []

    # --- Conexiones base (siempre activas) ---
    # Telemetría continua
    brain_mapper.data_updated.connect(main_window.update_brain_stats)
    
    # Voz
    main_window.mic_toggle_requested.connect(voice_worker.toggle_listening)
    voice_worker.listening_started.connect(lambda: main_window.set_listening_state(True))
    voice_worker.listening_stopped.connect(lambda: main_window.set_listening_state(False))
    voice_worker.error.connect(lambda e: main_window.mic_status.setText(f'<span style="color:#FF3B3B;">{e}</span>'))

    # --- Lógica Qwen vs Mock ---
    if QWEN_AVAILABLE:
        qwen_worker = None
        
        def on_qwen_ok(data):
            reply = data.get("reply", "No pude procesar tu respuesta.")
            emotion = data.get("emotion", "Neutral")
            region = data.get("region", "Frontal")
            intensity = float(data.get("intensity", 0.5))
            note = data.get("note", "")
            
            # Guardar en historial
            chat_history_qwen.append({"role": "assistant", "content": reply})
            
            # Enviar al chat
            main_window.append_chat_message(ChatMessage(Role.AI, reply))
            
            # Activar cerebro con datos CLÍNICOS reales
            result = BrainActivationResult(
                dominant_region=region,
                activation_level=intensity,
                emotional_state=emotion
            )
            main_window.handle_brain_activation(result)
            main_window.append_analysis_result(result)
            
            # Loguear sesión
            session_logger.log("ai_response", reply, {
                "emotion": emotion, "region": region, 
                "intensity": intensity, "clinical_note": note
            })
        
        def on_qwen_fail(error):
            print(f"⚠️ Qwen falló: {error}. Usando mock de respaldo.")
            # Si Qwen falla, el mock toma el control automáticamente
            interview_engine.process_user_input(last_text_sent)
        
        last_text_sent = ""
        
        def process_with_qwen(text):
            nonlocal qwen_worker, last_text_sent
            last_text_sent = text
            
            # Detener worker anterior si existe
            if qwen_worker and qwen_worker.isRunning():
                qwen_worker.terminate()
                qwen_worker.wait()
            
            # Añadir usuario al historial
            chat_history_qwen.append({"role": "user", "content": text})
            
            # Iniciar nueva petición
            qwen_worker = QwenRequest(text, history=chat_history_qwen[:-1])
            qwen_worker.finished_ok.connect(on_qwen_ok)
            qwen_worker.failed.connect(on_qwen_fail)
            qwen_worker.start()
        
        # Conectar señal directamente a Qwen (mock desactivado)
        main_window.send_message_signal.connect(process_with_qwen)
        voice_worker.transcript_ready.connect(process_with_qwen)
        
        print("✅ Puente Qwen conectado (Mock desactivado)")
        
    else:
        # Modo solo mock si no hay Qwen
        main_window.send_message_signal.connect(interview_engine.process_user_input)
        interview_engine.new_message.connect(main_window.append_chat_message)
        interview_engine.brain_activation.connect(main_window.handle_brain_activation)
        interview_engine.brain_activation.connect(main_window.append_analysis_result)
        
        voice_worker.transcript_ready.connect(interview_engine.process_user_input)
        
        print("⚠️ Qwen no disponible. Usando solo Mock.")

    # --- Registro de sesión (respuestas del paciente) ---
    def log_patient_answer(text):
        session_logger.log("patient_answer", text)
        # Mostrar burbuja del usuario inmediatamente
        main_window.append_chat_message(ChatMessage(Role.USER, text))
        main_window.thinking_label.show()
    
    voice_worker.transcript_ready.connect(log_patient_answer)
    # Para texto escrito, ya se muestra en hybrid_process/process_with_qwen antes de enviar
    
    brain_mapper.start_mapping()
    main_window.show()

    print(f" Sesión guardándose en: {session_logger.file_path}")
    main_window.append_chat_message(ChatMessage(Role.AI, "Sistema listo. Soy el Dr. García, neuropsicólogo. ¿Cómo te sientes hoy?"))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()