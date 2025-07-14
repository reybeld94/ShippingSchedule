# migrate_excel.py - Migración desde Excel a PostgreSQL
import pandas as pd
import requests
from datetime import datetime
import sys
import os

# Configuración
EXCEL_PATH = r"\\10.0.0.7\Production\Shipping Schedule.xlsx"
SHEET_NAME = "Shipping Schedule"
SERVER_URL = "http://localhost:8000"

# Credenciales para autenticación
USERNAME = "admin"
PASSWORD = "admin123"

def get_auth_token():
    """Obtener token de autenticación"""
    try:
        response = requests.post(f"{SERVER_URL}/login", json={
            "username": USERNAME,
            "password": PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            return data["access_token"]
        else:
            print("❌ Error en login")
            return None
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return None

def determine_status_from_colors(row_data):
    """
    Determinar el status basado en los datos
    """
    
    # Si tiene datos en "SHIPPED", es final_release
    if row_data.get('shipped') and str(row_data.get('shipped')).strip():
        return "final_release"
    
    # Si tiene QC RELEASE pero no SHIPPED, es partial_release
    if row_data.get('qc_release') and str(row_data.get('qc_release')).strip():
        return "partial_release"
    
    # Por defecto
    return "partial_release"

def clean_date_field(date_value):
    """Limpiar campos de fecha"""
    if pd.isna(date_value):
        return ""
    
    date_str = str(date_value).strip()
    
    # Si es "N/A" o similar, retornar vacío
    if date_str.upper() in ['N/A', 'NA', 'NULL', 'NONE', '']:
        return ""
    
    # Si ya está en formato MM/DD/YY, mantenerlo
    if '/' in date_str and len(date_str.split('/')) == 3:
        return date_str
    
    # Si es un timestamp de pandas, convertirlo
    try:
        if hasattr(date_value, 'strftime'):
            return date_value.strftime('%m/%d/%y')
    except:
        pass
    
    return date_str

def clear_existing_data(token):
    """Limpiar datos existentes (opcional)"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{SERVER_URL}/shipments", headers=headers)
        if response.status_code == 200:
            existing_shipments = response.json()
            print(f"🗑️ Encontrados {len(existing_shipments)} registros existentes")
            
            if len(existing_shipments) > 0:
                clear = input("¿Quieres eliminar todos los registros existentes antes de importar? (y/n): ").lower()
                if clear == 'y':
                    for shipment in existing_shipments:
                        requests.delete(f"{SERVER_URL}/shipments/{shipment['id']}", headers=headers)
                    print("✅ Registros existentes eliminados")
    except:
        pass

def migrate_excel_data():
    """Función principal de migración"""
    
    print("🚀 Iniciando migración desde Excel...")
    print(f"📁 Leyendo: {EXCEL_PATH}")
    
    # Verificar que el archivo existe
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ No se puede acceder al archivo: {EXCEL_PATH}")
        print("Verifica que:")
        print("- La ruta de red esté disponible")
        print("- Tengas permisos de lectura")
        print("- El archivo no esté abierto por otro usuario")
        return False
    
    # Obtener token de autenticación
    print("🔑 Obteniendo token de autenticación...")
    token = get_auth_token()
    if not token:
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Verificar conexión al servidor
    try:
        test_response = requests.get(f"{SERVER_URL}/shipments", headers=headers, timeout=5)
        if test_response.status_code != 200:
            print("❌ Error: No se puede conectar al servidor o el token es inválido")
            return False
        print("✅ Conexión al servidor verificada")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("Asegúrate de que el servidor esté corriendo (py main.py)")
        return False
    
    # Opción de limpiar datos existentes
    clear_existing_data(token)
    
    # Preguntar cómo manejar duplicados
    print("\n🔄 Manejo de Jobs duplicados:")
    print("1. Saltar duplicados (mantener el primero)")
    print("2. Sobrescribir duplicados (usar el último)")
    print("3. Crear con sufijo (ej: 38465.1, 38465.2)")
    
    duplicate_option = input("Elige opción (1/2/3): ").strip()
    if duplicate_option not in ['1', '2', '3']:
        duplicate_option = '1'  # Por defecto
    
    print(f"✅ Opción seleccionada: {duplicate_option}")
    
    # Contador para sufijos
    job_counters = {}
    
    try:
        # Leer Excel
        print(f"📖 Leyendo hoja '{SHEET_NAME}'...")
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, header=None)
        
        print(f"📊 Archivo leído: {len(df)} filas encontradas")
        
        # Mostrar las primeras filas para debug
        print("\n🔍 Primeras 5 filas del archivo:")
        print(df.head().to_string())
        
        # Empezar desde la fila 3 (índice 2)
        data_rows = df.iloc[2:]  # Omitir las primeras 2 filas
        
        print(f"\n📝 Procesando {len(data_rows)} filas de datos...")
        
        successful_imports = 0
        errors = []
        
        for index, row in data_rows.iterrows():
            try:
                # Mapeo según la captura - ajustado por los nombres reales:
                # A=0: JOB #, B=1: JOB NAME, C=2: DESCRIPTION, 
                # D=3: QC RELEASE, E=4: CREATED, F=5: SHIP PLAN, 
                # G=6: SHIPPED, H=7: Invoice #, I=8: SHIPPING NOTES
                
                job_number = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                job_name = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                description = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
                
                # Fechas
                qc_release = clean_date_field(row.iloc[3]) if len(row) > 3 else ""
                created = clean_date_field(row.iloc[4]) if len(row) > 4 else ""
                ship_plan = clean_date_field(row.iloc[5]) if len(row) > 5 else ""
                shipped = clean_date_field(row.iloc[6]) if len(row) > 6 else ""
                invoice_number = str(row.iloc[7]) if len(row) > 7 and pd.notna(row.iloc[7]) else ""
                shipping_notes = str(row.iloc[8]) if len(row) > 8 and pd.notna(row.iloc[8]) else ""
                
                # Campos que no están en tu Excel actual pero son requeridos
                shipping_list = job_name  # Usar job_name como shipping_list
                week = ""  # Campo vacío por ahora
                
                # Limpiar job_number
                job_number = job_number.replace('.0', '').strip()
                
                # Manejar duplicados según la opción elegida
                original_job_number = job_number
                
                if duplicate_option == '3':  # Crear con sufijo
                    if original_job_number in job_counters:
                        job_counters[original_job_number] += 1
                        job_number = f"{original_job_number}.{job_counters[original_job_number]}"
                    else:
                        job_counters[original_job_number] = 1
                
                # Validar que tenga datos mínimos
                if not job_number or job_number == 'nan' or len(job_number.strip()) == 0:
                    continue
                    
                if not shipping_list or shipping_list == 'nan':
                    continue
                    
                if not job_name or job_name == 'nan':
                    continue
                
                # Determinar status
                status = determine_status_from_colors({
                    'qc_release': qc_release,
                    'shipped': shipped
                })
                
                # Crear objeto para enviar
                shipment_data = {
                    "job_number": job_number,
                    "shipping_list": shipping_list,
                    "job_name": job_name,
                    "week": week,
                    "description": description,
                    "status": status,
                    "qc_release": qc_release,
                    "created": created,
                    "ship_plan": ship_plan,
                    "shipped": shipped,
                    "invoice_number": invoice_number,
                    "shipping_notes": shipping_notes
                }
                
                # Enviar al servidor
                if duplicate_option == '2':  # Sobrescribir duplicados
                    # Primero intentar actualizar si existe
                    existing_response = requests.get(f"{SERVER_URL}/shipments", headers=headers, timeout=10)
                    if existing_response.status_code == 200:
                        existing_shipments = existing_response.json()
                        existing_shipment = next((s for s in existing_shipments if s['job_number'] == job_number), None)
                        
                        if existing_shipment:
                            # Actualizar existente
                            response = requests.put(
                                f"{SERVER_URL}/shipments/{existing_shipment['id']}",
                                json=shipment_data,
                                headers=headers,
                                timeout=10
                            )
                            if response.status_code == 200:
                                successful_imports += 1
                                print(f"🔄 Actualizado: Job #{job_number} - {shipping_list}")
                                continue
                
                # Crear nuevo (opción 1, 3, o si falló la actualización)
                response = requests.post(
                    f"{SERVER_URL}/shipments",
                    json=shipment_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 201:
                    successful_imports += 1
                    print(f"✅ Importado: Job #{job_number} - {shipping_list}")
                elif response.status_code == 400:
                    try:
                        error_detail = response.json().get('detail', 'Bad request')
                        if 'already exists' in error_detail and duplicate_option == '1':
                            print(f"⚠️ Saltado (ya existe): Job #{job_number}")
                            continue  # Saltar este error si es duplicado y elegimos opción 1
                    except:
                        error_detail = f"HTTP {response.status_code}: {response.text[:100]}"
                    
                    errors.append(f"Job #{job_number}: {error_detail}")
                    print(f"❌ Error Job #{job_number}: {error_detail}")
                else:
                    try:
                        error_detail = response.json().get('detail', f'HTTP {response.status_code}')
                    except:
                        error_detail = f"HTTP {response.status_code}: {response.text[:100]}"
                    errors.append(f"Job #{job_number}: {error_detail}")
                    print(f"❌ Error Job #{job_number}: {error_detail}")
                
            except Exception as e:
                errors.append(f"Fila {index + 1}: {str(e)}")
                print(f"❌ Error procesando fila {index + 1}: {e}")
                continue
        
        # Resumen final
        print(f"\n📋 RESUMEN DE MIGRACIÓN:")
        print(f"✅ Exitosos: {successful_imports}")
        print(f"❌ Errores: {len(errors)}")
        
        if errors:
            print(f"\n🚨 DETALLES DE ERRORES:")
            for error in errors[:10]:  # Mostrar solo los primeros 10
                print(f"   • {error}")
            if len(errors) > 10:
                print(f"   ... y {len(errors) - 10} errores más")
        
        print(f"\n🎉 Migración completada!")
        return True
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚢 MIGRACIÓN DE SHIPPING SCHEDULE DESDE EXCEL")
    print("=" * 60)
    
    # Verificar dependencias
    try:
        import pandas as pd
        import openpyxl  # Necesario para leer Excel
    except ImportError:
        print("❌ Faltan dependencias. Instala con:")
        print("py -m pip install pandas openpyxl")
        sys.exit(1)
    
    success = migrate_excel_data()
    
    if success:
        print("\n✅ ¡Migración completada exitosamente!")
        print("Ahora puedes usar tu aplicación PyQt6 con todos los datos.")
    else:
        print("\n❌ La migración falló. Revisa los errores arriba.")
    
    input("\nPresiona Enter para salir...")
