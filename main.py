# main.py - Punto de entrada corregido
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Instanciar UI (el backend se conecta después cuando esté listo)
    main_window = MainWindow()
    
    # Conexiones básicas (descomenta cuando tengas el backend real)
    # main_window.send_message_signal.connect(interview_engine.process_user_input)
    # interview_engine.new_message.connect(main_window.append_chat_message)
    # brain_mapper.data_updated.connect(main_window.update_brain_stats)

    # Iniciar aplicación
    main_window.show()
    
    # Mensaje de bienvenida inicial
    try:
        from corebackend_skeleton import ChatMessage, Role
        main_window.append_chat_message(ChatMessage(Role.AI, "Enlace neural establecido. Bienvenido."))
    except ImportError:
        pass  # Si no hay backend, la UI sigue funcionando igual

    sys.exit(app.exec())

if __name__ == "__main__":
    main()