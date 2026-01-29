# Estación Meteorológica Satelital IoT (ESP32 + Myriota Ultra Lite)

> **Sistema autónomo de monitoreo ambiental con transmisión Direct-to-Orbit (DtO) y persistencia de datos histórica.**

![Estado](https://img.shields.io/badge/Estado-Operativo-green?style=for-the-badge)
![Hardware](https://img.shields.io/badge/Hardware-ESP32_%7C_Myriota_Ultra_Lite-blue?style=for-the-badge)
![Backend](https://img.shields.io/badge/Backend-Python_%7C_InfluxDB_%7C_Docker-orange?style=for-the-badge)

## Descripción del Proyecto 

Este proyecto implementa una solución de ingeniería completa para la telemetría remota en zonas sin cobertura celular ni internet. Utiliza el módulo **Myriota Ultra Lite** para enviar paquetes de datos comprimidos a través de una constelación de nanosatélites LEO (Low Earth Orbit).

El sistema resuelve desafíos críticos de la comunicación satelital, como la latencia, la sincronización de tiempos y el ahorro de energía, mediante un firmware personalizado y un backend inteligente.

## Características Principales

### Firmware (ESP32)
* **Protocolo "Handshake":** Algoritmo de sincronización (`AT` -> `OK`) que asegura que el módem esté despierto antes de enviar datos, eliminando la pérdida de paquetes.
* **Time-Aware (Reloj Satelital):** El ESP32 consulta el reloj atómico del satélite (`AT+TIME=?`) e inyecta un *Timestamp* real en el payload. Esto garantiza que el dato tenga la hora exacta de la medición, no la hora de llegada al servidor.
* **Diagnóstico en Pantalla:** Interfaz OLED que muestra en tiempo real el estado del módem (`READY`, `GPS_ACQ`), la cola de mensajes (`Queue`) y el resultado del último envío.
* **Ciclo Inteligente:** Envío inicial rápido (30s) seguido de ciclos de 10 minutos.

### Backend (Python + InfluxDB)
* **Batch Processing:** El script puente recupera lotes de 100 mensajes históricos de TagoIO, los ordena cronológicamente y los inserta en la base de datos, recuperando información acumulada durante las ventanas de desconexión satelital.
* **Data Cleaning:** Algoritmo de limpieza que detecta y elimina el *padding* (relleno) basura que a veces añade la red satelital.
* **Infraestructura Docker:** Despliegue contenerizado de InfluxDB para persistencia de datos.

## Arquitectura de Hardware

| Componente | Modelo Específico | Función |
| :--- | :--- | :--- |
| **Microcontrolador** | ESP32 DevKit V1 | Cerebro y control |
| **Módem Satelital** | **Myriota Ultra Lite** | Transmisión DtO (VHF/UHF) |
| **Sensor** | DHT11 | Temperatura y Humedad |
| **Pantalla** | OLED SSD1306 (0.96") | Interfaz HMI de diagnóstico |

### Diagrama de Conexiones (Pinout)

Es crítico respetar estas conexiones para evitar conflictos con el Boot del ESP32 y el Reset del OLED.

| Pin ESP32 | Conexión | Notas Técnicas (Troubleshooting) |
| :--- | :--- | :--- |
| **GPIO 16 (RX2)** | **Myriota TX** | ⚠️ **CRÍTICO:** Este pin suele ser usado por librerías OLED como RESET. Se debe configurar el OLED con `RST=-1` para liberar la línea. |
| **GPIO 17 (TX2)** | **Myriota RX** | Comunicación UART a 9600 baudios. |
| **GPIO 27** | **Myriota BUSY** | Lectura de estado (HIGH = Ocupado/Tx). |
| **GPIO 21** | **OLED SDA** | I2C |
| **GPIO 22** | **OLED SCL** | I2C |
| **GPIO 14** | **DHT11 Data** | Sensor |
| **3.3V / GND** | **VCC / GND** | Alimentación común. |

## Estructura del Payload (Hexadecimal)

Para optimizar el costo y ancho de banda (limitado a 24 bytes), se envía una trama hexadecimal compacta de **16 caracteres (8 bytes)**:

`TTTTHHHHZZZZZZZZ`

* **`TTTT` (2 bytes):** Temperatura * 100. (Ej: `0789` -> 19.29 °C)
* **`HHHH` (2 bytes):** Humedad * 100. (Ej: `172A` -> 59.30 %)
* **`ZZZZZZZZ` (4 bytes):** Timestamp Unix Satelital. (Ej: `65AE4F00` -> Fecha exacta)

## Instalación y Despliegue

### 1. Firmware
1.  Abrir el proyecto en **PlatformIO** o **Arduino IDE**.
2.  Instalar dependencias: `Adafruit SSD1306`, `Adafruit GFX`, `DHT sensor library`.
3.  Cargar `firmware/main.cpp` en el ESP32.

### 2. Base de Datos (Docker)
Levantar el contenedor de InfluxDB:
```bash
cd database
docker-compose up -d
```

### 3. Puente de Datos (Python)
Configurar el entorno y ejecutar el script ETL:
```bash
cd backend
pip install -r requirements.txt
# Crear archivo config.py con tu TOKEN de TagoIO
python puente_real.py
```

## Notas 

1.  **Conflicto GPIO 16:** La librería Adafruit OLED bloquea el puerto Serial RX2 por defecto. Se solucionó instanciando `Adafruit_SSD1306 display(..., -1);`.
2.  **Myriota Protocol:** El módulo Ultra Lite requiere terminadores `\r` (CR) estrictos. El uso de `\n` (LF) o `\r\n` combinados puede causar errores de comando desconocido.
3.  **Latencia LEO:** Debido a la naturaleza orbital, los datos no son tiempo real. El uso del *Timestamp Satelital* embebido en el payload es obligatorio para mantener la integridad científica de los datos históricos.



