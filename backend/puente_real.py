import os
import sys
import requests
import time
from influxdb import InfluxDBClient
from datetime import datetime

# --- CONFIGURACIÓN SEGURA (DOCKER) ---
TAGO_TOKEN = os.getenv('TAGO_TOKEN')
INFLUX_HOST = os.getenv('INFLUX_HOST', 'influxdb')
INFLUX_PORT = int(os.getenv('INFLUX_PORT', 8086))
INFLUX_DB = os.getenv('INFLUX_DB', 'myriota_db')

print(f"--- PUENTE SATELITAL INICIADO ---")
print(f"Conectando a DB: {INFLUX_HOST}:{INFLUX_PORT}")

# Conexión a InfluxDB
try:
    client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)
    client.switch_database(INFLUX_DB)
except Exception as e:
    print(f"Error conectando a InfluxDB: {e}")

ultimo_time_procesado = None 

def obtener_lote_datos():
    url = "https://api.tago.io/data"
    headers = {"Device-Token": TAGO_TOKEN}
    params = {"qty": 100} 
    
    try:
        response = requests.get(url, headers=headers, params=params)
        datos = response.json()
        if datos and datos.get('status') and len(datos.get('result', [])) > 0:
            return datos['result']
        return []
    except Exception as e:
        print(f"Error conexión API Tago: {e}")
        return []

print("Buscando datos históricos y nuevos...")

while True:
    lote = obtener_lote_datos()
    
    if lote:
        # Ordenamos por fecha
        lote_ordenado = sorted(lote, key=lambda x: x['time'])
        nuevos_procesados = 0

        for dato in lote_ordenado:
            timestamp_llegada = dato['time']

            # Filtramos para no repetir datos viejos
            if ultimo_time_procesado is None or timestamp_llegada > ultimo_time_procesado:
                
                # --- LIMPIEZA ROBUSTA ---
                try:
                    raw_payload = str(dato['value'])
                    # 1. Quitamos comillas, espacios y comas extras
                    raw_payload = raw_payload.replace('"', '').replace("'", "").replace(',', '').strip()
                    
                    # 2. Quitamos relleno de Myriota (CCCC...)
                    if "CCCC" in raw_payload:
                        raw_payload = raw_payload.split("CCCC")[0]

                    # 3. Validamos longitud mínima (8 caracteres para Temp+Hum)
                    if len(raw_payload) >= 8:
                        
                        # Decodificación Hexadecimal
                        hex_temp = raw_payload[0:4]
                        hex_hum = raw_payload[4:8]
                        
                        temp_val = int(hex_temp, 16) / 100.0
                        hum_val = int(hex_hum, 16) / 100.0
                        
                        # Lógica de Timestamp Satelital
                        tiempo_final = timestamp_llegada
                        usando_tiempo_satelital = False

                        if len(raw_payload) == 16:
                            hex_time = raw_payload[8:16]
                            try:
                                ts_satelite = int(hex_time, 16)
                                if ts_satelite > 0:
                                    tiempo_final = ts_satelite * 1000000000
                                    usando_tiempo_satelital = True
                            except:
                                pass # Si falla el tiempo, usamos el de llegada

                        # Guardar en InfluxDB
                        json_body = [{
                            "measurement": "sensores_esp32",
                            "tags": {
                                "origen": "Satelite",
                                "dispositivo": "Myriota_UltraLite"
                            },
                            "time": tiempo_final,
                            "fields": {
                                "temperatura": temp_val,
                                "humedad": hum_val,
                                "raw_hex": raw_payload,
                                "ts_type": "satelite" if usando_tiempo_satelital else "servidor"
                            }
                        }]
                        client.write_points(json_body)
                        
                        origen_txt = "SAT" if usando_tiempo_satelital else "SRV"
                        print(f"[GUARDADO] {tiempo_final} ({origen_txt}) | T:{temp_val}°C H:{hum_val}%")
                        nuevos_procesados += 1
                        
                        ultimo_time_procesado = timestamp_llegada
                    else:
                        # Dato muy corto o basura, lo saltamos pero avanzamos el tiempo
                        ultimo_time_procesado = timestamp_llegada

                except Exception as e:
                    print(f"[ERROR DATO] {e} en payload: {dato['value']}")
                    # Avanzamos para no quedarnos pegados en el error
                    ultimo_time_procesado = timestamp_llegada

        if nuevos_procesados > 0:
            print(f" -> {nuevos_procesados} nuevos registros.")
            
    # Espera de 30 segundos
    time.sleep(30)