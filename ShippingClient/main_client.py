# main_client.py - Archivo principal modular
import sys
import os
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QFont, QIcon

# Imports locales
from ui.login_dialog import ModernLoginDialog
from core.config import MODERN_FONT, ICON_PATH, get_font_size

def main():
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    # Configurar fuente del sistema
    font = QFont(MODERN_FONT, get_font_size())
    app.setFont(font)
    
    # Estilo de aplicación moderno
    app.setStyle('Fusion')
    
    try:
        # Login
        print("Starting application...")
        login_dialog = ModernLoginDialog()
        
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            print("Login successful, opening main window...")
            
            # Importar dinámicamente para evitar problemas de inicialización
            from ui.main_window import ModernShippingMainWindow
            
            # Mostrar ventana principal
            main_window = ModernShippingMainWindow(login_dialog.token, login_dialog.user_info)
            main_window.show()
            
            return app.exec()
        else:
            print("Login cancelado")
            return 0
            
    except Exception as e:
        print(f"Critical application error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
