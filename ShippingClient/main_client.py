# main_client.py - Archivo principal modular
import sys
import os
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt6.QtGui import QFont, QIcon

# Imports locales
from ui.login_dialog import ModernLoginDialog
from ui.theme import apply_fluent_theme
from core import config as app_config
from core.config import MODERN_FONT, ICON_PATH, get_font_size, ensure_font_available

def main():
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    # Use a neutral base style so our QSS controls the look across platforms
    app.setStyle('Fusion')

    # Install the global Fluent theme (typography + QSS for every widget).
    # apply_fluent_theme picks Segoe UI Variable when available and falls
    # back to MODERN_FONT-equivalent families on other OSes.
    user_font_size = get_font_size()
    resolved_family = apply_fluent_theme(app, point_size=user_font_size)

    # Keep MODERN_FONT in sync for legacy callers that still reference it.
    app_config.MODERN_FONT = resolved_family or ensure_font_available(MODERN_FONT)
    
    try:
        # Login
        print("Starting application...")
        login_dialog = ModernLoginDialog()
        
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            print("Login successful, opening main window...")
            
            # Importar dinamicamente para evitar problemas de inicializacion
            from ui.main_window import ModernShippingMainWindow
            
            # Mostrar ventana principal
            try:
                main_window = ModernShippingMainWindow(login_dialog.token, login_dialog.user_info)
                main_window.showMaximized()
            except Exception as init_error:
                print(f"Failed to initialize main window: {init_error}")
                import traceback
                traceback.print_exc()
                error_dialog = QMessageBox()
                error_dialog.setIcon(QMessageBox.Icon.Critical)
                error_dialog.setWindowTitle("Application Error")
                error_dialog.setText(f"Failed to open the application window:\n\n{init_error}")
                error_dialog.exec()
                return 1
            
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
