# utils.py

import pandas as pd
import xml.etree.ElementTree as ET

# Definición de las constantes de archivos
FILES = {
    'S_BASE_ENERGIA': 'S_reporte_energia.csv',
    'NS_BASE_ENERGIA': 'NS_reporte_energia.csv',
    'S_ATTK_ENERGIA': 'S_reporte_energia_ATTK.csv',
    'NS_ATTK_ENERGIA': 'NS_reporte_energia_ATTK.csv',
    'S_BASE_METRICAS': 'S_metricas.xml',
    'NS_BASE_METRICAS': 'NS_metricas.xml',
    'S_ATTK_METRICAS': 'S_metricas-ATTK.xml',
    'NS_ATTK_METRICAS': 'NS_metrica-ATTK.xml',
    # Archivos de animación (NetAnim)
    'S_BASE_ANIM': 'S_iot-animacion.xml',
    'NS_BASE_ANIM': 'NS_iot-animacion.xml',
    'S_ATTK_ANIM': 'S_iot-animacion-ATTK.xml',
    'NS_ATTK_ANIM': 'NS_iot-animacion_ATTK.xml',
}

def load_energy_data(file_key):
    """Carga y calcula el consumo de energía promedio de un archivo CSV."""
    df = pd.read_csv(FILES[file_key])
    df['Escenario'] = 'S_con_Seguridad' if file_key.startswith('S_') else 'NS_sin_Seguridad'
    df['Tipo'] = 'Base' if 'BASE' in file_key else 'Ataque'
    # Columna combinada para filtros en la barra lateral
    df['Escenario_Completo'] = df['Escenario'] + ' - ' + df['Tipo']
    return df

def convert_ns_to_s(ns_str):
    """Función auxiliar para limpiar y convertir valores de nanosegundos a segundos."""
    try:
        clean_str = ns_str.strip().replace('+', '').replace('ns', '')
        # Si la cadena ya usa notación científica, Python lo maneja directamente.
        ns_value = float(clean_str)
        return ns_value / 1e9
    except (ValueError, AttributeError):
        return 0.0

def parse_histogram(flow_element, histogram_tag, scenario_completo):
    """Parsea los datos de un histograma (delay o jitter) en un DataFrame."""
    hist_element = flow_element.find(f'{histogram_tag}Histogram')
    data = []
    if hist_element is not None:
        for bin_elem in hist_element.findall('bin'):
            data.append({
                'Escenario_Completo': scenario_completo,
                'Métrica': histogram_tag.capitalize(),
                'Rango_Inicio (s)': float(bin_elem.get('start')),
                'Rango_Ancho (s)': float(bin_elem.get('width')),
                'Conteo': int(bin_elem.get('count'))
            })
    return pd.DataFrame(data)

def get_base_metrics(root, scenario_completo):
    """Extrae métricas clave del FlowMonitor (Flow ID 1)."""
    flow = root.find(".//Flow[@flowId='1']")
    
    # Inicializar métricas base
    base_metrics = {
        'Retardo_Sum (s)': 0.0, 'Jitter_Sum (s)': 0.0,
        'TX_Bytes': 0, 'RX_Packets': 0, 'Lost_Packets': 0,
        'Retardo_Promedio (s)': 0.0, 'Jitter_Promedio (s)': 0.0,
        'Bytes_x_Paquete': 0.0,
        'df_delay_hist': pd.DataFrame(), 'df_jitter_hist': pd.DataFrame()
    }

    if flow is None: return base_metrics

    # 1. Extracción y Conversión
    retardo_s = convert_ns_to_s(flow.get('delaySum', '0ns'))
    jitter_s = convert_ns_to_s(flow.get('jitterSum', '0ns'))
    tx_bytes = int(flow.get('txBytes', 0))
    rx_packets = int(flow.get('rxPackets', 0))
    lost_packets = int(flow.get('lostPackets', 0))

    # 2. Cálculos de Promedio
    # Usaremos RX_Packets para los promedios de Jitter y Retardo (solo aplica a paquetes recibidos)
    divisor = rx_packets if rx_packets > 0 else 1 
    
    retardo_promedio = retardo_s / divisor
    jitter_promedio = jitter_s / divisor
    
    # Cálculo de Sobrecarga
    bytes_per_packet = tx_bytes / divisor if divisor > 0 else 0

    # 3. Parseo de Histogramas
    df_delay_hist = parse_histogram(flow, 'delay', scenario_completo)
    df_jitter_hist = parse_histogram(flow, 'jitter', scenario_completo)

    # 4. Consolidación
    base_metrics.update({
        'Retardo_Sum (s)': retardo_s,
        'Jitter_Sum (s)': jitter_s,
        'TX_Bytes': tx_bytes,
        'RX_Packets': rx_packets,
        'Lost_Packets': lost_packets,
        'Retardo_Promedio (s)': retardo_promedio,
        'Jitter_Promedio (s)': jitter_promedio,
        'Bytes_x_Paquete': bytes_per_packet,
        'df_delay_hist': df_delay_hist,
        'df_jitter_hist': df_jitter_hist
    })
    
    return base_metrics

def get_energy_summary(df):
    """Calcula el resumen de energía promedio."""
    summary = df.groupby('Escenario_Completo')['Energia_Consumida(J)'].agg(['mean', 'sum']).reset_index()
    summary.rename(columns={'mean': 'Energia_Promedio(J)', 'sum': 'Energia_Total(J)'}, inplace=True)
    summary[['Escenario', 'Tipo']] = summary['Escenario_Completo'].str.split(' - ', expand=True)
    
    return summary

def load_netanim_data(file_key):
    """Carga y procesa datos de animación NetAnim para Plotly."""
    file_path = FILES[file_key]
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    motion_data = []

    # 1. Obtener posiciones iniciales (tiempo 0)
    for node in root.findall('node'):
        node_id = int(node.get('id'))
        pos = {
            'X': float(node.get('locX')),
            'Y': float(node.get('locY'))
        }
        motion_data.append({'Time': 0.0, 'Node_ID': node_id, 'X': pos['X'], 'Y': pos['Y']})

    # 2. Procesar movimientos
    for move in root.findall('move'):
        node_id = int(move.get('id'))
        time = float(move.get('time'))
        
        locX_str = move.get('locX')
        locY_str = move.get('locY')
        
        if locX_str is not None and locY_str is not None:
            motion_data.append({
                'Time': time,
                'Node_ID': node_id,
                'X': float(locX_str),
                'Y': float(locY_str)
            })

    df = pd.DataFrame(motion_data)
    
    if df.empty:
        return pd.DataFrame(columns=['Time', 'Node_ID', 'X', 'Y'])
        
    # Llenar movimientos faltantes (nodos estáticos) para la animación fluida
    df = df.sort_values(by=['Node_ID', 'Time']).reset_index(drop=True)
    df_pivot = df.pivot(index='Time', columns='Node_ID', values=['X', 'Y'])
    df_pivot = df_pivot.fillna(method='ffill') 
    
    df_motion = df_pivot.stack(level=1, dropna=False).reset_index()
    df_motion.columns = ['Time', 'Node_ID', 'X', 'Y']
    
    return df_motion


def load_all_data():
    """Carga y procesa todos los datos para la aplicación (Energía, Métricas, Histogramas)."""
    
    # 1. Carga de Energía
    df_list = []
    for k in FILES:
        if 'ENERGIA' in k:
            try:
                df_list.append(load_energy_data(k))
            except Exception as e:
                # print(f"Error al cargar el archivo de energía {FILES[k]}: {e}")
                pass
                
    if not df_list:
        df_energia = pd.DataFrame(columns=['Nodo_ID', 'Energia_Consumida(J)', 'Escenario', 'Tipo', 'Escenario_Completo'])
    else:
        df_energia = pd.concat(df_list, ignore_index=True)

    # 2. Carga y Consolidación de Métricas (FlowMonitor)
    metricas_data = []
    hist_data = []
    
    for key in FILES:
        if 'METRICAS' in key:
            try:
                escenario_completo = f"{'S_con_Seguridad' if key.startswith('S_') else 'NS_sin_Seguridad'} - {'Base' if 'BASE' in key else 'Ataque'}"
                tree = ET.parse(FILES[key])
                root = tree.getroot()
                metrics = get_base_metrics(root, escenario_completo)
                
                # Consolidar métricas principales
                metricas_data.append({
                    'Escenario': 'S_con_Seguridad' if key.startswith('S_') else 'NS_sin_Seguridad',
                    'Tipo': 'Base' if 'BASE' in key else 'Ataque',
                    'Escenario_Completo': escenario_completo,
                    'Retardo_Sum (s)': metrics['Retardo_Sum (s)'],
                    'Jitter_Sum (s)': metrics['Jitter_Sum (s)'],
                    'Retardo_Promedio (s)': metrics['Retardo_Promedio (s)'],
                    'Jitter_Promedio (s)': metrics['Jitter_Promedio (s)'],
                    'Bytes_x_Paquete': metrics['Bytes_x_Paquete'],
                    'Paquetes_RX': metrics['RX_Packets'],
                    'Paquetes_Perdidos': metrics['Lost_Packets']
                })
                
                # Consolidar datos de histograma
                if not metrics['df_delay_hist'].empty:
                    hist_data.append(metrics['df_delay_hist'])
                if not metrics['df_jitter_hist'].empty:
                    hist_data.append(metrics['df_jitter_hist'])
                
            except Exception as e:
                # print(f"Error al cargar el archivo de métricas {FILES[key]}: {e}")
                pass
            
    df_metricas = pd.DataFrame(metricas_data)
    
    if hist_data:
        df_histograms = pd.concat(hist_data, ignore_index=True)
    else:
        df_histograms = pd.DataFrame(columns=['Escenario_Completo', 'Métrica', 'Rango_Inicio (s)', 'Rango_Ancho (s)', 'Conteo'])
    
    return df_energia, df_metricas, df_histograms