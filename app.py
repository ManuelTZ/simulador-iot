# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_all_data, get_energy_summary, load_netanim_data, FILES

# Configuración de la página (Título y layout)
st.set_page_config(
    page_title="Dashboard de Análisis de IoT y Seguridad",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Carga de Datos y Caching ---
@st.cache_data
def load_data_and_summary():
    """Carga y procesa datos, incluyendo métricas e histogramas."""
    df_energia, df_metricas, df_histograms = load_all_data()
    
    if df_energia.empty:
        df_energia_summary = pd.DataFrame(columns=['Escenario_Completo', 'Energia_Promedio(J)', 'Energia_Total(J)', 'Escenario', 'Tipo'])
    else:
        df_energia_summary = get_energy_summary(df_energia)
        
    return df_energia, df_metricas, df_energia_summary, df_histograms

@st.cache_data
def load_all_netanim_data():
    """Carga todos los datos de animación disponibles."""
    anim_keys = [k for k in FILES if 'ANIM' in k]
    all_df = []
    for key in anim_keys:
        try:
            df = load_netanim_data(key)
            scenario_name = f"{'S_con_Seguridad' if key.startswith('S_') else 'NS_sin_Seguridad'} - {'Base' if 'BASE' in key else 'Ataque'}"
            df['Escenario_Completo'] = scenario_name
            all_df.append(df)
        except Exception as e:
            # print(f"Error cargando archivo NetAnim {key}: {e}")
            pass
            
    if not all_df:
        return pd.DataFrame(columns=['Time', 'Node_ID', 'X', 'Y', 'Escenario_Completo'])
        
    return pd.concat(all_df, ignore_index=True)

# Cargar todos los datos
df_energia, df_metricas, df_energia_summary, df_histograms = load_data_and_summary()
df_netanim = load_all_netanim_data()

# Obtener lista única de escenarios para el filtro
unique_scenarios = sorted(df_metricas['Escenario_Completo'].unique().tolist())
if not unique_scenarios:
     unique_scenarios = ['No data']

# --- Diseño de la Interfaz ---
st.title("🛡️ Análisis de Rendimiento y Seguridad en Redes IoT")
st.markdown("## Comparativa de Escenarios Base y Ataque (NetSim)")
st.markdown("---")


# --- BARRA LATERAL (Filtros Globales) ---
st.sidebar.header("Filtros de Escenario")
select_all = st.sidebar.checkbox("Seleccionar Todos los Escenarios", value=True)

if select_all:
    selected_scenarios = unique_scenarios
else:
    selected_scenarios = st.sidebar.multiselect(
        "Selecciona Escenario(s)",
        options=unique_scenarios,
        default=unique_scenarios
    )

# Filtro de DataFrames Globales
df_metricas_filtered = df_metricas[df_metricas['Escenario_Completo'].isin(selected_scenarios)]
df_energia_summary_filtered = df_energia_summary[df_energia_summary['Escenario_Completo'].isin(selected_scenarios)]


# --- Pestañas de Navegación ---
tab_comparativa, tab_distribucion, tab_simulacion, tab_animacion, tab_resumen = st.tabs([
    "📈 Métricas Clave y KPIs",
    "📉 Distribución de Retardo/Jitter",
    "⚡ Análisis de Consumo de Energía",
    "📽️ Animación de Nodos",
    "📝 Resumen Ejecutivo"
])


# --- Pestaña 1: Comparativa de Métricas Clave y KPIs ---
with tab_comparativa:
    st.header("Análisis de Rendimiento: Retardo, Paquetes y Sobrecarga")

    if df_metricas_filtered.empty:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
    else:
        # --- Implementación de KPIs ---
        st.subheader("Indicadores Clave de Rendimiento (KPIs)")
        
        # Encontrar los valores para los KPIs (Se usan datos sin filtrar para la comparativa S vs NS Ataque)
        energy_attack_S = df_energia_summary[df_energia_summary['Escenario_Completo'] == 'S_con_Seguridad - Ataque']['Energia_Promedio(J)'].values
        energy_attack_NS = df_energia_summary[df_energia_summary['Escenario_Completo'] == 'NS_sin_Seguridad - Ataque']['Energia_Promedio(J)'].values
        lost_ns_attack = df_metricas[df_metricas['Escenario_Completo'] == 'NS_sin_Seguridad - Ataque']['Paquetes_Perdidos'].sum()
        
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        
        # KPI 1: Efectividad de la Seguridad (Ahorro de Energía)
        if energy_attack_S.size > 0 and energy_attack_NS.size > 0 and energy_attack_NS[0] > 0:
            diff = energy_attack_NS[0] - energy_attack_S[0]
            pct_saving = (diff / energy_attack_NS[0]) * 100
            
            col_kpi1.metric(
                label="Ahorro de Energía bajo Ataque (S vs NS)",
                value=f"{diff:.2f} J",
                delta=f"Efectividad: {pct_saving:.1f}%"
            )
        else:
             col_kpi1.metric(label="Ahorro de Energía bajo Ataque", value="N/A", delta="Faltan datos de Ataque")
        
        # KPI 2: Paquetes Perdidos bajo Ataque NS (Riesgo máximo)
        col_kpi2.metric(
            label="Paquetes Perdidos Sin Seguridad (Ataque)",
            value=f"{lost_ns_attack}",
        )
        
        # KPI 3: Peor Retardo Promedio
        if not df_metricas_filtered.empty:
            worst_delay = df_metricas_filtered['Retardo_Promedio (s)'].max()
            scenario_worst = df_metricas_filtered.loc[df_metricas_filtered['Retardo_Promedio (s)'].idxmax()]['Escenario_Completo']
            col_kpi3.metric(
                label="Peor Retardo Promedio (s)",
                value=f"{worst_delay:.4f} s",
                delta=f"Escenario: {scenario_worst}"
            )
        else:
            col_kpi3.metric(label="Peor Retardo Promedio (s)", value="0.0000 s")


        st.markdown("---")
        st.subheader("Tabla de Métricas de Rendimiento por Flow (ID 1)")
        
        # Muestra la tabla de métricas (renombrada para mejor UX)
        st.dataframe(
            df_metricas_filtered.rename(columns={
                'Retardo_Sum (s)': 'Retardo Total (s)', 
                'Jitter_Sum (s)': 'Jitter Total (s)',
                'Retardo_Promedio (s)': 'Retardo Promedio (s)',
                'Jitter_Promedio (s)': 'Jitter Promedio (s)',
                'Bytes_x_Paquete': 'Sobrecarga (Bytes/Paquete)',
                'Paquetes_RX': 'Paquetes Recibidos',
                'Paquetes_Perdidos': 'Paquetes Perdidos'
            }), 
            hide_index=True, 
            width='stretch'
        )
        
        col_g1, col_g2 = st.columns(2)
        
        # Gráfico 1: Retardo Promedio (Nuevo)
        with col_g1:
            fig_delay_avg = px.bar(
                df_metricas_filtered, 
                x='Escenario_Completo', 
                y='Retardo_Promedio (s)', 
                color='Escenario_Completo',
                title='Retardo Promedio por Paquete (Segundos)',
                labels={'Retardo_Promedio (s)': 'Retardo Promedio (s)', 'Escenario_Completo': 'Escenario'}
            )
            st.plotly_chart(fig_delay_avg, width='stretch')

        # Gráfico 2: Jitter Promedio (Nuevo)
        with col_g2:
            fig_jitter_avg = px.bar(
                df_metricas_filtered, 
                x='Escenario_Completo', 
                y='Jitter_Promedio (s)', 
                color='Escenario_Completo',
                title='Jitter Promedio por Paquete (Segundos)',
                labels={'Jitter_Promedio (s)': 'Jitter Promedio (s)', 'Escenario_Completo': 'Escenario'}
            )
            st.plotly_chart(fig_jitter_avg, width='stretch')
            
        col_g3, col_g4 = st.columns(2)

        # Gráfico 3: Paquetes Perdidos (Nuevo)
        with col_g3:
            fig_lost = px.bar(
                df_metricas_filtered, 
                x='Escenario_Completo', 
                y='Paquetes_Perdidos', 
                color='Escenario_Completo',
                title='Paquetes Perdidos',
                labels={'Paquetes_Perdidos': 'Cantidad de Paquetes Perdidos', 'Escenario_Completo': 'Escenario'}
            )
            st.plotly_chart(fig_lost, width='stretch')

        # Gráfico 4: Sobrecarga/Overhead
        with col_g4:
            fig_overhead = px.bar(
                df_metricas_filtered, 
                x='Escenario_Completo', 
                y='Bytes_x_Paquete', 
                color='Escenario_Completo',
                title='Sobrecarga (Bytes/Paquete)',
                labels={'Bytes_x_Paquete': 'Bytes por Paquete (Overhead)', 'Escenario_Completo': 'Escenario'}
            )
            st.plotly_chart(fig_overhead, width='stretch')

# --- Pestaña 2: Distribución de Retardo/Jitter (NUEVA) ---
with tab_distribucion:
    st.header("📉 Distribución de Frecuencia de Retardo y Jitter")
    st.info("Estos gráficos muestran la frecuencia (conteo) con la que los valores de retardo y jitter caen dentro de rangos específicos (bins).")

    df_hist_filtered = df_histograms[df_histograms['Escenario_Completo'].isin(selected_scenarios)]

    if df_hist_filtered.empty:
        st.warning("No hay datos de histograma disponibles para los escenarios seleccionados.")
    else:
        # Gráfico de Histograma de Retardo
        df_delay_hist = df_hist_filtered[df_hist_filtered['Métrica'] == 'Delay']
        
        if not df_delay_hist.empty:
            fig_delay_hist = px.bar(
                df_delay_hist,
                x='Rango_Inicio (s)',
                y='Conteo',
                color='Escenario_Completo',
                barmode='group',
                title='Histograma de Retardo de Paquetes (Segundos)',
                labels={'Rango_Inicio (s)': 'Rango de Retardo (s)', 'Conteo': 'Conteo de Paquetes'}
            )
            fig_delay_hist.update_xaxes(type='category')
            st.plotly_chart(fig_delay_hist, width='stretch')
        else:
             st.info("No hay datos de Histograma de Retardo disponibles.")
             
        st.markdown("---")

        # Gráfico de Histograma de Jitter
        df_jitter_hist = df_hist_filtered[df_hist_filtered['Métrica'] == 'Jitter']
        
        if not df_jitter_hist.empty:
            fig_jitter_hist = px.bar(
                df_jitter_hist,
                x='Rango_Inicio (s)',
                y='Conteo',
                color='Escenario_Completo',
                barmode='group',
                title='Histograma de Jitter de Paquetes (Segundos)',
                labels={'Rango_Inicio (s)': 'Rango de Jitter (s)', 'Conteo': 'Conteo de Paquetes'}
            )
            fig_jitter_hist.update_xaxes(type='category')
            st.plotly_chart(fig_jitter_hist, width='stretch')
        else:
             st.info("No hay datos de Histograma de Jitter disponibles.")


# --- Pestaña 3: Análisis de Consumo de Energía ---
with tab_simulacion:
    st.header("⚡ Análisis de Consumo de Energía")
    
    # Tabla Resumen (filtrada)
    st.subheader("Resumen de Consumo de Energía por Escenario")
    st.dataframe(
        df_energia_summary_filtered.drop(columns=['Escenario', 'Tipo']), 
        hide_index=True, 
        width='stretch'
    )
    
    col3, col4 = st.columns(2)
    
    # Gráfico de Consumo Promedio
    with col3:
        fig_energy = px.bar(
            df_energia_summary_filtered, 
            x='Escenario_Completo', 
            y='Energia_Promedio(J)', 
            color='Escenario_Completo',
            title='Consumo de Energía Promedio por Nodo (Julios)',
            labels={'Energia_Promedio(J)': 'Energía Promedio Consumida (J)', 'Escenario_Completo': 'Escenario'}
        )
        st.plotly_chart(fig_energy, width='stretch')
        
    # Gráfico de Consumo por Nodo (Interactiva - Simulable)
    with col4:
        st.subheader("Visualización Detallada por Nodo")
        
        if not df_energia.empty:
            scenario_options = df_energia['Escenario_Completo'].unique().tolist()
            if not scenario_options:
                st.warning("No hay datos de energía para graficar el detalle por nodo.")
            else:
                selected_detail_scenario = st.selectbox(
                    "Selecciona el Escenario para Detalle de Nodo",
                    scenario_options
                )
                
                filtered_df = df_energia[
                    df_energia['Escenario_Completo'] == selected_detail_scenario
                ]
                
                fig_node_energy = px.line(
                    filtered_df, 
                    x='Nodo_ID', 
                    y='Energia_Consumida(J)', 
                    title=f'Consumo de Energía por Nodo - {selected_detail_scenario}',
                    labels={'Energia_Consumida(J)': 'Energía Consumida (J)', 'Nodo_ID': 'ID del Nodo'}
                )
                st.plotly_chart(fig_node_energy, width='stretch')
        else:
            st.warning("No hay datos de energía cargados para simular.")


# --- Pestaña 4: Animación de Nodos Interactiva ---
with tab_animacion:
    st.header("📽️ Visualización Dinámica de Movimiento de Nodos")
    
    if df_netanim.empty:
        st.warning("⚠️ No se pudo cargar ningún archivo de animación XML. Asegúrate de que los archivos NetAnim estén en el directorio correcto.")
    else:
        st.info("Simulación del movimiento de la topología usando Plotly. El eje de tiempo (Time) en la parte inferior controla la animación.")
        
        # Controles de Simulación
        scenario_options_anim = df_netanim['Escenario_Completo'].unique().tolist()
        if not scenario_options_anim:
            st.warning("No hay escenarios de animación disponibles.")
        else:
            selected_anim_scenario = st.selectbox(
                "Selecciona el Escenario de Animación",
                scenario_options_anim
            )
            
            filtered_anim_df = df_netanim[df_netanim['Escenario_Completo'] == selected_anim_scenario].copy()
            
            if not filtered_anim_df.empty:
                # Crear la animación de dispersión (Scatter Plot)
                fig_anim = px.scatter(
                    filtered_anim_df, 
                    x='X', 
                    y='Y', 
                    animation_frame='Time',
                    color='Node_ID', 
                    hover_name='Node_ID',
                    size=[15]*len(filtered_anim_df), 
                    range_x=[filtered_anim_df['X'].min() - 5, filtered_anim_df['X'].max() + 5],
                    range_y=[filtered_anim_df['Y'].min() - 5, filtered_anim_df['Y'].max() + 5],
                    title=f"Animación de Topología: {selected_anim_scenario}",
                    labels={'X': 'Coordenada X', 'Y': 'Coordenada Y'}
                )
                
                fig_anim.update_layout(
                    transition={'duration': 100},
                    yaxis = {'scaleanchor':"x", 'scaleratio':1},
                    margin=dict(t=50, b=50, l=50, r=50)
                )
                
                if fig_anim.layout.updatemenus:
                    fig_anim.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 100 
                    fig_anim.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 50

                st.plotly_chart(fig_anim, width='stretch')
            else:
                st.warning("No hay datos de movimiento disponibles para el escenario seleccionado.")


# --- Pestaña 5: Resumen Ejecutivo y Conclusión ---
with tab_resumen:
    st.header("📝 Resumen Ejecutivo y Conclusión")
    st.markdown("El análisis detallado del rendimiento y consumo de energía permite extraer las siguientes conclusiones clave:")
    
    st.subheader("1. Costo Operacional de la Seguridad (Caso Base)")
    st.success("La seguridad en el caso base (sin ataque) tiene un **costo operacional bajo**:")
    
    # Cálculos de Sobrecarga
    df_base = df_metricas[df_metricas['Tipo'] == 'Base']
    avg_overhead_s = df_base[df_base['Escenario'] == 'S_con_Seguridad']['Bytes_x_Paquete'].mean()
    avg_overhead_ns = df_base[df_base['Escenario'] == 'NS_sin_Seguridad']['Bytes_x_Paquete'].mean()
    overhead_diff = avg_overhead_s - avg_overhead_ns if not pd.isna(avg_overhead_s) and not pd.isna(avg_overhead_ns) else 0

    st.markdown(f"* **Sobrecarga (Overhead):** La seguridad añade $\\approx **{overhead_diff:.0f} bytes**$ por paquete (comparando S\_Base vs NS\_Base).")
    
    # Cálculos de Energía
    energy_base_s = df_energia_summary[df_energia_summary['Escenario_Completo'] == 'S_con_Seguridad - Base']['Energia_Promedio(J)'].values
    energy_base_ns = df_energia_summary[df_energia_summary['Escenario_Completo'] == 'NS_sin_Seguridad - Base']['Energia_Promedio(J)'].values

    if energy_base_s.size > 0 and energy_base_ns.size > 0 and energy_base_ns[0] > 0:
        energy_diff = energy_base_s[0] - energy_base_ns[0]
        energy_pct = (energy_diff / energy_base_ns[0]) * 100
        st.markdown(f"* **Energía:** Solo $\\approx **{energy_pct:.1f}\\%**$ de aumento en el consumo promedio por nodo.")
    else:
        st.markdown("* **Energía:** No hay datos de energía base para el cálculo de comparación.")
        
    st.subheader("2. Efectividad de la Defensa frente al Ataque")
    st.error("El ataque (probablemente DoS de agotamiento de recursos) impacta críticamente el escenario no seguro:")
    
    # Cálculos de Ataque
    energy_attack_S_val = energy_attack_S[0] if energy_attack_S.size > 0 else 0
    energy_attack_NS_val = energy_attack_NS[0] if energy_attack_NS.size > 0 else 0
    lost_s_attack = df_metricas[df_metricas['Escenario_Completo'] == 'S_con_Seguridad - Ataque']['Paquetes_Perdidos'].sum()
    lost_ns_attack = df_metricas[df_metricas['Escenario_Completo'] == 'NS_sin_Seguridad - Ataque']['Paquetes_Perdidos'].sum()
    
    if energy_attack_S_val > 0 and energy_attack_NS_val > 0 and energy_base_ns.size > 0 and energy_base_s.size > 0:
        factor_increase_ns = energy_attack_NS_val / energy_base_ns[0] if energy_base_ns[0] > 0 else float('inf')
        factor_increase_s = energy_attack_S_val / energy_base_s[0] if energy_base_s[0] > 0 else float('inf')
        
        st.markdown(f"* **Sin Seguridad (NS - Ataque):** El consumo se dispara a $\\approx **{energy_attack_NS_val:.2f} J**$, un aumento de **{factor_increase_ns:.1f} veces** respecto a NS\_Base. Se registraron $\\mathbf{{lost_ns_attack}}$ paquetes perdidos.")
        st.success(f"* **Con Seguridad (S - Ataque):** El consumo se mantiene controlado a $\\approx **{energy_attack_S_val:.2f} J**$, un aumento de solo **{factor_increase_s:.1f} veces** respecto a S\_Base. Paquetes perdidos: $\\mathbf{{lost_s_attack}}$")
        
    st.markdown("---")
    st.metric(
        label="Conclusión Principal", 
        value="La seguridad es **crítica y altamente efectiva**", 
        delta=f"La inversión previene una pérdida de energía catastrófica y garantiza un servicio estable bajo ataque."
    )