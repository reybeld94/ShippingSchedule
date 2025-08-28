# main_client.py - Archivo principal modular
import sys
import os
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QFont, QIcon

# Imports locales
from ui.login_dialog import ModernLoginDialog
from core.config import MODERN_FONT, FONT_SIZE, ICON_PATH

def main():
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    # Configurar fuente del sistema
    font = QFont(MODERN_FONT, FONT_SIZE)
    app.setFont(font)
    
    # Estilo de aplicación moderno
    app.setStyle('Fusion')
    
    try:
        # Login
        print("Iniciando aplicación...")
        login_dialog = ModernLoginDialog()
        
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            print("Login exitoso, abriendo ventana principal...")
            
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
        print(f"Error crítico en la aplicación: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
