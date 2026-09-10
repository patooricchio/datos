import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Visor Climatológico - Argentina", page_icon="🌤️", layout="wide")

# CSS personalizado para adaptar métricas a pantallas chicas (notebooks 13")
st.markdown("""
<style>
    div[data-testid="stMetricValue"] > div {
        font-size: 1.4rem !important;
    }
    div[data-testid="stMetricLabel"] > label {
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    # Carga rápida del parquet presintetizado y optimizado
    df_merged = pd.read_parquet("estaciones.parquet")
    
    # Cargar nómina de estaciones para metadatos y mapas
    df_nomina = pd.read_csv("nomina_estaciones.csv", dtype={"id_estacion": str})
    
    return df_merged, df_nomina

try:
    df, df_nomina = load_data()
except Exception as e:
    st.error(f"Error al cargar archivos: {e}")
    st.stop()

# --- BARRA LATERAL: FILTROS ---
st.sidebar.title("🎛️ Filtros de Selección")

# Obtener lista de provincias únicas
provincias_unicas = sorted([p for p in df["provincia"].cat.categories if p in df["provincia"].values]) if isinstance(df["provincia"].dtype, pd.CategoricalDtype) else sorted(df["provincia"].dropna().unique())
provincias = ["Todas"] + list(provincias_unicas)
prov_sel = st.sidebar.selectbox("Seleccionar Provincia", provincias)

df_filtrado = df[df["provincia"] == prov_sel] if prov_sel != "Todas" else df
estaciones = sorted([e for e in df_filtrado["nombre"].dropna().unique()])

if not estaciones:
    st.sidebar.warning("No hay estaciones disponibles.")
    st.stop()

estacion_sel = st.sidebar.selectbox("Seleccionar Estación", estaciones)

min_fecha, max_fecha = df_filtrado["fecha"].min().date(), df_filtrado["fecha"].max().date()
fechas_sel = st.sidebar.date_input("Rango de Fechas", value=(min_fecha, max_fecha), min_value=min_fecha, max_value=max_fecha)


# --- FILTRO POR MESES CON CHECKBOXES INTERACTIVOS Y OPCIÓN 'TODOS' ---
st.sidebar.markdown("### 📅 Filtro por Meses")

dict_meses = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Inicialización de estados en session_state la primera vez
if "todos_meses" not in st.session_state:
    st.session_state["todos_meses"] = True
    for num_mes in dict_meses:
        st.session_state[f"chk_mes_{num_mes}"] = True

# Función callback para actualizar todos los meses cuando cambia el checkbox "Todos"
def toggle_todos_meses():
    nuevo_estado = st.session_state["todos_meses"]
    for num_mes in dict_meses:
        st.session_state[f"chk_mes_{num_mes}"] = nuevo_estado

# Función callback para actualizar el checkbox "Todos" si se desmarca algún mes individual
def actualizar_estado_todos():
    todos_activos = all(st.session_state.get(f"chk_mes_{m}", False) for m in dict_meses)
    st.session_state["todos_meses"] = todos_activos

# Checkbox maestro "Todos"
st.sidebar.checkbox(
    "Seleccionar Todos los Meses",
    key="todos_meses",
    on_change=toggle_todos_meses
)

meses_sel = []

# Desplegable con 2 columnas (6 filas de 2 meses)
with st.sidebar.expander("Seleccionar Meses", expanded=True):
    col_mes1, col_mes2 = st.columns(2)
    
    for num_mes, nombre_mes in dict_meses.items():
        col_actual = col_mes1 if num_mes % 2 != 0 else col_mes2
        
        check = col_actual.checkbox(
            nombre_mes,
            key=f"chk_mes_{num_mes}",
            on_change=actualizar_estado_todos
        )
        if check:
            meses_sel.append(num_mes)

# Validación en caso de que no haya meses seleccionados
if not meses_sel:
    st.sidebar.warning("Por favor, selecciona al menos un mes para ver los datos.")
    st.stop()

fecha_inicio, fecha_fin = (fechas_sel[0], fechas_sel[1]) if isinstance(fechas_sel, tuple) and len(fechas_sel) == 2 else (min_fecha, max_fecha)

df_estacion = df[
    (df["nombre"] == estacion_sel) & 
    (df["fecha"].dt.date >= fecha_inicio) & 
    (df["fecha"].dt.date <= fecha_fin) &
    (df["fecha"].dt.month.isin(meses_sel))
].sort_values("fecha")

info_estacion = df_nomina[df_nomina["nombre"] == estacion_sel].iloc[0]

# --- ENCABEZADO ---
st.title(f"📊 {info_estacion['nombre']}")
st.caption(f"**Provincia:** {info_estacion['provincia']} | **ID:** {info_estacion['id_estacion']} | **Altitud:** {info_estacion['altura']} msnm")

# --- TARJETAS DE MÉTRICAS ---
if not df_estacion.empty:
    idx_tmax = df_estacion['tmax'].idxmax() if df_estacion['tmax'].notnull().any() else None
    val_tmax = df_estacion.loc[idx_tmax, 'tmax'] if idx_tmax is not None else None
    fecha_tmax = df_estacion.loc[idx_tmax, 'fecha'].strftime('%d/%m/%Y') if idx_tmax is not None else "N/D"

    idx_tmin = df_estacion['tmin'].idxmin() if df_estacion['tmin'].notnull().any() else None
    val_tmin = df_estacion.loc[idx_tmin, 'tmin'] if idx_tmin is not None else None
    fecha_tmin = df_estacion.loc[idx_tmin, 'fecha'].strftime('%d/%m/%Y') if idx_tmin is not None else "N/D"

    df_estacion_anio = df_estacion.copy()
    df_estacion_anio['anio'] = df_estacion_anio['fecha'].dt.year
    precip_anual_series = df_estacion_anio.groupby('anio')['precip'].sum()
    if not precip_anual_series.empty:
        max_anio = precip_anual_series.idxmax()
        max_anio_val = precip_anual_series.max()
        str_anio = f"{max_anio}"
        str_precip = f"{max_anio_val:,.1f} mm acumulados"
    else:
        str_anio, str_precip = "N/D", ""
        
    cant_datos = len(df_estacion)
else:
    val_tmax, fecha_tmax = None, "N/D"
    val_tmin, fecha_tmin = None, "N/D"
    str_anio, str_precip = "N/D", ""
    cant_datos = 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Tº Máx. Absoluta", f"{val_tmax:.1f} °C" if pd.notnull(val_tmax) else "N/D", delta=f"Ocurrió el {fecha_tmax}", delta_color="off")
with col2:
    st.metric("Tº Mín. Absoluta", f"{val_tmin:.1f} °C" if pd.notnull(val_tmin) else "N/D", delta=f"Ocurrió el {fecha_tmin}", delta_color="off")
with col3:
    st.metric("Año con Mayor Precipitación", str_anio, delta=str_precip, delta_color="off")
with col4:
    st.metric("Cantidad de Registros", f"{cant_datos:,} días")

st.markdown("---")

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Series Diarias", "🗓️ Comparativa ENSO / Interanual", "🗺️ Visor Geográfico", "📋 Tablas y Resúmenes"])

# 1. SERIES DIARIAS
with tab1:
    if df_estacion.empty:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
    else:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=df_estacion['fecha'], y=df_estacion['tmax'], mode='lines', name='T. Máx (°C)', line=dict(color='#d9534f')))
        fig_temp.add_trace(go.Scatter(x=df_estacion['fecha'], y=df_estacion['tmin'], mode='lines', name='T. Mín (°C)', line=dict(color='#0275d8')))
        fig_temp.update_layout(title="Temperaturas Diarias", hovermode="x unified")
        st.plotly_chart(fig_temp, width='content')

        fig_precip = px.bar(df_estacion, x='fecha', y='precip', title="Precipitación Diaria (mm)", color_discrete_sequence=['#5bc0de'])
        st.plotly_chart(fig_precip, width='content')

# 2. COMPARATIVA ENSO / INTERANUAL
with tab2:
    st.subheader("Análisis Interanual y Fases ENOS")
    
    if df_estacion.empty:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
    else:
        df_estacion_copy = df_estacion.copy()
        df_estacion_copy['mes_num'] = df_estacion_copy['fecha'].dt.month
        df_estacion_copy['anio_str'] = df_estacion_copy['fecha'].dt.year.astype(str)
        df_estacion_copy['anio'] = df_estacion_copy['fecha'].dt.year
        
        # --- 1. Gráfico de Curvas Comparativas Interanuales ---
        df_mensual = df_estacion_copy.groupby(['anio_str', 'mes_num'])['precip'].sum(min_count=1).reset_index()
        
        fig_interanual = px.line(
            df_mensual,
            x='mes_num',
            y='precip',
            color='anio_str',
            markers=True,
            title="Evolución de Precipitación Mensual por Año (Curvas Comparativas)",
            labels={'mes_num': 'Mes del Año', 'precip': 'Precipitación (mm)', 'anio_str': 'Año'}
        )
        
        tick_vals = list(dict_meses.keys())
        tick_texts = [dict_meses[m][:3] for m in tick_vals]
        
        fig_interanual.update_layout(
            xaxis=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_texts)
        )
        st.plotly_chart(fig_interanual, width='content')
        
        st.markdown("---")
        
        # --- 2. Clasificación Oficial ENOS y Gráfico de Barras Cronológico ---
        TABLA_ENSO = {
            "1980-1981": "Neutral", "1981-1982": "Neutral", "1982-1983": "El Niño",
            "1983-1984": "La Niña", "1984-1985": "La Niña", "1985-1986": "Neutral",
            "1986-1987": "El Niño", "1987-1988": "El Niño", "1988-1989": "La Niña",
            "1989-1990": "Neutral", "1990-1991": "Neutral", "1991-1992": "El Niño",
            "1992-1993": "Neutral", "1993-1994": "Neutral", "1994-1995": "El Niño",
            "1995-1996": "La Niña", "1996-1997": "Neutral", "1997-1998": "El Niño",
            "1998-1999": "La Niña", "1999-2000": "La Niña", "2000-2001": "La Niña",
            "2001-2002": "Neutral", "2002-2003": "El Niño", "2003-2004": "Neutral",
            "2004-2005": "El Niño", "2005-2006": "La Niña", "2006-2007": "El Niño",
            "2007-2008": "La Niña", "2008-2009": "La Niña", "2009-2010": "El Niño",
            "2010-2011": "La Niña", "2011-2012": "La Niña", "2012-2013": "Neutral",
            "2013-2014": "Neutral", "2014-2015": "El Niño", "2015-2016": "El Niño",
            "2016-2017": "Neutral", "2017-2018": "La Niña", "2018-2019": "El Niño",
            "2019-2020": "El Niño", "2020-2021": "La Niña", "2021-2022": "La Niña",
            "2022-2023": "La Niña", "2023-2024": "El Niño", "2024-2025": "La Niña",
            "2025-2026": "Neutral"
        }
        
        def obtener_fase_enos(anio):
            for clave, fase in TABLA_ENSO.items():
                if clave.startswith(str(anio)):
                    return fase
            return "Sin Datos"

        df_anual_enos = df_estacion_copy.groupby('anio')['precip'].sum(min_count=1).reset_index()
        df_anual_enos['Fase ENOS'] = df_anual_enos['anio'].apply(obtener_fase_enos)
        
        # Filtrar años fuera del rango
        df_anual_enos = df_anual_enos[df_anual_enos['Fase ENOS'] != "Sin Datos"].sort_values('anio')
        
        # Obtener el orden cronológico estricto de los años
        orden_anios = df_anual_enos['anio'].tolist()

        fig_enos_bar = px.bar(
            df_anual_enos,
            x='anio',
            y='precip',
            color='Fase ENOS',
            title="Precipitación Total Anual según Clasificación ENOS (Orden Cronológico)",
            labels={'anio': 'Año', 'precip': 'Precipitación Acumulada (mm)', 'Fase ENOS': 'Fase ENOS'},
            color_discrete_map={
                "El Niño": "#d9534f",   # Rojo
                "La Niña": "#0275d8",   # Azul
                "Neutral": "#6c757d"    # Gris
            },
            category_orders={'anio': orden_anios}  # Forzar el orden del eje X
        )
        fig_enos_bar.update_xaxes(type='category')
        st.plotly_chart(fig_enos_bar, width='content')

# 3. VISOR GEOGRÁFICO
with tab3:
    st.subheader("Mapa de Ubicación de Estaciones")
    df_mapa = df_nomina.dropna(subset=['lat', 'lon']).copy()
    df_mapa['Estado'] = df_mapa['nombre'].apply(lambda x: "Estación Seleccionada" if x == estacion_sel else "Otras Estaciones")
    
    fig_map = px.scatter_geo(
        df_mapa,
        lat="lat",
        lon="lon",
        hover_name="nombre",
        hover_data=["provincia", "altura", "id_estacion"],
        color="Estado",
        color_discrete_map={"Estación Seleccionada": "#d9534f", "Otras Estaciones": "#0275d8"},
        size=df_mapa['Estado'].apply(lambda x: 14 if x == "Estación Seleccionada" else 6),
        scope="south america",
        center={"lat": info_estacion['lat'], "lon": info_estacion['lon']},
        projection="mercator"
    )
    
    fig_map.update_layout(
        height=600,
        margin={"r":0,"t":10,"l":0,"b":0},
        geo=dict(
            showland=True, landcolor="rgb(243, 243, 243)",
            showcountries=True, countrycolor="rgb(204, 204, 204)",
            showsubunits=True, subunitcolor="rgb(204, 204, 204)",
            fitbounds="locations"
        )
    )
    st.plotly_chart(fig_map, width='content')

# 4. TABLAS Y RESÚMENES
with tab4:
    subtab1, subtab2, subtab3 = st.tabs(["🗓️ Resumen Mensual", "🌧️ Precipitación Anual", "📄 Datos Diarios Crudos"])
    
    if df_estacion.empty:
        st.warning("No hay datos para calcular resúmenes.")
    else:
        df_estacion_calc = df_estacion.copy()
        df_estacion_calc['tmedia'] = (df_estacion_calc['tmax'] + df_estacion_calc['tmin']) / 2
        
        # SUB-PESTAÑA 1: RESUMEN MENSUAL
        with subtab1:
            st.subheader("Resumen Climatológico por Año-Mes")
            df_estacion_calc['Año_Mes'] = df_estacion_calc['fecha'].dt.to_period('M')
            
            resumen_mensual = []
            for periodo, group in df_estacion_calc.groupby('Año_Mes'):
                idx_max = group['tmax'].idxmax() if group['tmax'].notnull().any() else None
                idx_min = group['tmin'].idxmin() if group['tmin'].notnull().any() else None
                
                f_max = group.loc[idx_max, 'fecha'].strftime('%d/%m/%Y') if idx_max is not None else "-"
                f_min = group.loc[idx_min, 'fecha'].strftime('%d/%m/%Y') if idx_min is not None else "-"
                
                resumen_mensual.append({
                    "Año-Mes": str(periodo),
                    "T. Media (°C)": round(group['tmedia'].mean(), 1),
                    "T. Máx. Absoluta (°C)": group['tmax'].max(),
                    "Fecha T. Máx": f_max,
                    "T. Mín. Absoluta (°C)": group['tmin'].min(),
                    "Fecha T. Mín": f_min,
                    "Precip. Acumulada (mm)": round(group['precip'].sum(), 1),
                    "Días con Lluvia": int((group['precip'] > 0.1).sum()),
                    "Cantidad de Datos": len(group)
                })
                
            df_resumen_m = pd.DataFrame(resumen_mensual)
            
            fig_bar_m = px.bar(
                df_resumen_m,
                x="Año-Mes",
                y="Precip. Acumulada (mm)",
                title="Evolución de la Precipitación Acumulada Mensual",
                color_discrete_sequence=['#0275d8']
            )
            fig_bar_m.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_bar_m, width='content')
            
            st.dataframe(df_resumen_m, width='content', hide_index=True)
            
            csv_m = df_resumen_m.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Resumen Mensual (CSV)", csv_m, f"Resumen_Mensual_{estacion_sel}.csv", "text/csv")

        # SUB-PESTAÑA 2: PRECIPITACIÓN ANUAL
        with subtab2:
            st.subheader("Precipitación Total por Año")
            df_estacion_calc['anio'] = df_estacion_calc['fecha'].dt.year
            
            resumen_anual = []
            for anio, group in df_estacion_calc.groupby('anio'):
                idx_pmax = group['precip'].idxmax() if group['precip'].notnull().any() else None
                f_pmax = group.loc[idx_pmax, 'fecha'].strftime('%d/%m/%Y') if idx_pmax is not None else "-"
                v_pmax = group.loc[idx_pmax, 'precip'] if idx_pmax is not None else 0.0
                
                resumen_anual.append({
                    "Año": anio,
                    "Precip. Acumulada (mm)": round(group['precip'].sum(), 1),
                    "Máxima en 24h (mm)": v_pmax,
                    "Fecha Máx. 24h": f_pmax,
                    "Días con Precipitación (>0.1mm)": int((group['precip'] > 0.1).sum()),
                    "Cantidad de Datos": len(group)
                })
                
            df_resumen_a = pd.DataFrame(resumen_anual)
            
            fig_bar_a = px.bar(
                df_resumen_a,
                x="Año",
                y="Precip. Acumulada (mm)",
                text_auto='.1f',
                title="Evolución de la Precipitación Acumulada Anual",
                color_discrete_sequence=['#5bc0de']
            )
            fig_bar_a.update_xaxes(type='category')
            st.plotly_chart(fig_bar_a, width='content')
            
            st.dataframe(df_resumen_a, width='content', hide_index=True)
            
            csv_a = df_resumen_a.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Precipitación Anual (CSV)", csv_a, f"Precipitación_Anual_{estacion_sel}.csv", "text/csv")

        # SUB-PESTAÑA 3: DATOS DIARIOS CRUDOS
        with subtab3:
            st.subheader("Registros Diarios")
            df_export = df_estacion[['id_estacion', 'nombre', 'provincia', 'fecha', 'tmax', 'tmin', 'precip']].copy()
            df_export['fecha'] = df_export['fecha'].dt.strftime('%Y-%m-%d')
            
            st.dataframe(df_export, width='content', hide_index=True)
            
            csv_d = df_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Datos Diarios (CSV)", csv_d, f"Datos_Diarios_{estacion_sel}.csv", "text/csv")