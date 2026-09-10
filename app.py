import os
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Visor Climatológico - Argentina", page_icon="🌤️", layout="wide"
)

# CSS personalizado para métricas
st.markdown(
    """
<style>
    div[data-testid="stMetricValue"] > div { font-size: 1.4rem !important; }
    div[data-testid="stMetricLabel"] > label { font-size: 0.85rem !important; }
    div[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

TABLA_ENSO = {
    "1980-1981": "Neutral",
    "1981-1982": "Neutral",
    "1982-1983": "El Niño",
    "1983-1984": "La Niña",
    "1984-1985": "La Niña",
    "1985-1986": "Neutral",
    "1986-1987": "El Niño",
    "1987-1988": "El Niño",
    "1988-1989": "La Niña",
    "1989-1990": "Neutral",
    "1990-1991": "Neutral",
    "1991-1992": "El Niño",
    "1992-1993": "Neutral",
    "1993-1994": "Neutral",
    "1994-1995": "El Niño",
    "1995-1996": "La Niña",
    "1996-1997": "Neutral",
    "1997-1998": "El Niño",
    "1998-1999": "La Niña",
    "1999-2000": "La Niña",
    "2000-2001": "La Niña",
    "2001-2002": "Neutral",
    "2002-2003": "El Niño",
    "2003-2004": "Neutral",
    "2004-2005": "El Niño",
    "2005-2006": "La Niña",
    "2006-2007": "El Niño",
    "2007-2008": "La Niña",
    "2008-2009": "La Niña",
    "2009-2010": "El Niño",
    "2010-2011": "La Niña",
    "2011-2012": "La Niña",
    "2012-2013": "Neutral",
    "2013-2014": "Neutral",
    "2014-2015": "El Niño",
    "2015-2016": "El Niño",
    "2016-2017": "Neutral",
    "2017-2018": "La Niña",
    "2018-2019": "El Niño",
    "2019-2020": "El Niño",
    "2020-2021": "La Niña",
    "2021-2022": "La Niña",
    "2022-2023": "La Niña",
    "2023-2024": "El Niño",
    "2024-2025": "La Niña",
    "2025-2026": "Neutral",
}


def obtener_fase_enso_fecha(dt):
  anio = dt.year
  mes = dt.month
  ciclo = f"{anio}-{anio + 1}" if mes >= 7 else f"{anio - 1}-{anio}"
  return TABLA_ENSO.get(ciclo, "Neutral")


def limpiar_id(val):
  """Remueve letras (como la 'A'), espacios o caracteres raros para dejar solo los dígitos."""
  if pd.isna(val):
    return ""
  val_str = str(val).strip().upper()
  # Extrae solo los dígitos numéricos de la cadena
  digitos = re.sub(r"\D", "", val_str)
  return digitos if digitos else val_str


@st.cache_data
def load_data():
  # 1. RED CONVENCIONAL
  df_conv = pd.read_parquet("estaciones.parquet")
  try:
    df_nomina_conv = pd.read_csv(
        "nomina_estaciones_corregida.csv", dtype={"id_estacion": str}
    )
  except FileNotFoundError:
    df_nomina_conv = pd.read_csv(
        "nomina_estaciones.csv", dtype={"id_estacion": str}
    )

  df_conv["id_estacion"] = df_conv["id_estacion"].apply(limpiar_id)
  df_nomina_conv["id_estacion"] = df_nomina_conv["id_estacion"].apply(
      limpiar_id
  )
  df_conv["fecha"] = pd.to_datetime(df_conv["fecha"])

  for col in ["nombre", "provincia"]:
    if col in df_conv.columns:
      df_conv = df_conv.drop(columns=[col])

  df_conv = df_conv.merge(
      df_nomina_conv[["id_estacion", "nombre", "provincia"]],
      on="id_estacion",
      how="left",
  )

  # 2. RED AUTOMÁTICA (EMAS)
  df_auto = pd.DataFrame()
  df_nomina_emas = pd.DataFrame()

  if os.path.exists("listado_emas.csv"):
    df_nomina_emas = pd.read_csv(
        "listado_emas.csv", sep=None, engine="python", encoding="latin-1"
    )

    renombrar_dict = {}
    for col in df_nomina_emas.columns:
      col_lower = col.strip().lower()
      if col_lower in ["id", "id_estacion"]:
        renombrar_dict[col] = "id_estacion"
      elif col_lower == "nombre":
        renombrar_dict[col] = "nombre"
      elif col_lower == "provincia":
        renombrar_dict[col] = "provincia"
      elif col_lower == "latitud":
        renombrar_dict[col] = "lat"
      elif col_lower == "longitud":
        renombrar_dict[col] = "lon"

    df_nomina_emas = df_nomina_emas.rename(columns=renombrar_dict)

    # Limpiar e igualar IDs en la nómina (remueve la 'A')
    df_nomina_emas["id_estacion"] = df_nomina_emas["id_estacion"].apply(
        limpiar_id
    )

    if "altura" not in df_nomina_emas.columns:
      df_nomina_emas["altura"] = 0

  if os.path.exists("estaciones_automaticas.parquet"):
    df_auto = pd.read_parquet("estaciones_automaticas.parquet")

    if "Id" in df_auto.columns:
      df_auto = df_auto.rename(columns={"Id": "id_estacion"})

    # Limpiar e igualar IDs en las mediciones
    df_auto["id_estacion"] = df_auto["id_estacion"].apply(limpiar_id)
    df_auto["fecha"] = pd.to_datetime(df_auto["fecha"])

    for col in ["nombre", "provincia"]:
      if col in df_auto.columns:
        df_auto = df_auto.drop(columns=[col])

    if not df_nomina_emas.empty:
      df_auto = df_auto.merge(
          df_nomina_emas[["id_estacion", "nombre", "provincia"]],
          on="id_estacion",
          how="left",
      )

  return df_conv, df_nomina_conv, df_auto, df_nomina_emas

try:
  df_conv, df_nomina_conv, df_auto, df_nomina_emas = load_data()
except Exception as e:
  st.error(f"Error al cargar archivos base: {e}")
  st.stop()

# --- BARRA LATERAL: SELECTOR DE RED Y FILTROS ---
st.sidebar.title("🎛️ Configuración y Filtros")

tipo_red = st.sidebar.radio(
    "Seleccionar Red de Estaciones",
    ["Convencionales (SMN / INTA)", "Automáticas (EMAS)"],
)

if tipo_red == "Convencionales (SMN / INTA)":
  df_active = df_conv
  df_nomina_active = df_nomina_conv
else:
  df_active = df_auto
  df_nomina_active = df_nomina_emas
  if df_active.empty:
    st.sidebar.warning(
        "⚠️ No se encontraron registros en 'estaciones_automaticas.parquet'."
    )
    st.stop()

provincias_unicas = sorted(df_nomina_active["provincia"].dropna().unique())
provincias = ["Todas"] + list(provincias_unicas)
prov_sel = st.sidebar.selectbox("Seleccionar Provincia", provincias)

if prov_sel != "Todas":
  df_nomina_filtrada = df_nomina_active[
      df_nomina_active["provincia"] == prov_sel
  ]
else:
  df_nomina_filtrada = df_nomina_active

estaciones = sorted(df_nomina_filtrada["nombre"].dropna().unique())

if not estaciones:
  st.sidebar.warning("No hay estaciones disponibles para esta selección.")
  st.stop()

estacion_sel = st.sidebar.selectbox("Seleccionar Estación", estaciones)

min_fecha, max_fecha = (
    df_active["fecha"].min().date(),
    df_active["fecha"].max().date(),
)

fechas_sel = st.sidebar.date_input(
    "Rango de Fechas",
    value=(min_fecha, max_fecha),
    min_value=min_fecha,
    max_value=max_fecha,
)

# --- FILTRO POR MESES ---
st.sidebar.markdown("### 📅 Filtro por Meses")
dict_meses = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

if "todos_meses" not in st.session_state:
  st.session_state["todos_meses"] = True
  for num_mes in dict_meses:
    st.session_state[f"chk_mes_{num_mes}"] = True


def toggle_todos_meses():
  nuevo_estado = st.session_state["todos_meses"]
  for num_mes in dict_meses:
    st.session_state[f"chk_mes_{num_mes}"] = nuevo_estado


def actualizar_estado_todos():
  todos_activos = all(
      st.session_state.get(f"chk_mes_{m}", False) for m in dict_meses
  )
  st.session_state["todos_meses"] = todos_activos


st.sidebar.checkbox(
    "Seleccionar Todos los Meses",
    key="todos_meses",
    on_change=toggle_todos_meses,
)
meses_sel = []

with st.sidebar.expander("Seleccionar Meses", expanded=True):
  col_mes1, col_mes2 = st.columns(2)
  for num_mes, nombre_mes in dict_meses.items():
    col_actual = col_mes1 if num_mes % 2 != 0 else col_mes2
    check = col_actual.checkbox(
        nombre_mes, key=f"chk_mes_{num_mes}", on_change=actualizar_estado_todos
    )
    if check:
      meses_sel.append(num_mes)

if not meses_sel:
  st.warning("Seleccioná al menos un mes para visualizar los datos.")
  st.stop()

fecha_inicio, fecha_fin = (
    (fechas_sel[0], fechas_sel[1])
    if isinstance(fechas_sel, tuple) and len(fechas_sel) == 2
    else (min_fecha, max_fecha)
)

info_estacion = df_nomina_active[
    df_nomina_active["nombre"] == estacion_sel
].iloc[0]
id_estacion_sel = str(info_estacion["id_estacion"])

df_estacion = df_active[
    (df_active["id_estacion"] == id_estacion_sel)
    & (df_active["fecha"].dt.date >= fecha_inicio)
    & (df_active["fecha"].dt.date <= fecha_fin)
    & (df_active["fecha"].dt.month.isin(meses_sel))
].sort_values("fecha")

# --- ENCABEZADO ---
st.title(f"📊 {info_estacion['nombre']} ({tipo_red})")
alt_val = info_estacion.get("altura", "N/D")
st.caption(
    f"**Provincia:** {info_estacion['provincia']} | **ID:**"
    f" {id_estacion_sel} | **Altitud:** {alt_val} msnm"
)

# --- TARJETAS DE MÉTRICAS ---
if not df_estacion.empty:
  idx_tmax = (
      df_estacion["tmax"].idxmax()
      if df_estacion["tmax"].notnull().any()
      else None
  )
  val_tmax = (
      df_estacion.loc[idx_tmax, "tmax"] if idx_tmax is not None else None
  )
  fecha_tmax = (
      df_estacion.loc[idx_tmax, "fecha"].strftime("%d/%m/%Y")
      if idx_tmax is not None
      else "N/D"
  )

  idx_tmin = (
      df_estacion["tmin"].idxmin()
      if df_estacion["tmin"].notnull().any()
      else None
  )
  val_tmin = (
      df_estacion.loc[idx_tmin, "tmin"] if idx_tmin is not None else None
  )
  fecha_tmin = (
      df_estacion.loc[idx_tmin, "fecha"].strftime("%d/%m/%Y")
      if idx_tmin is not None
      else "N/D"
  )

  df_estacion_anio = df_estacion.copy()
  df_estacion_anio["anio"] = df_estacion_anio["fecha"].dt.year
  precip_anual_series = df_estacion_anio.groupby("anio")["precip"].sum()
  if not precip_anual_series.empty:
    max_anio = precip_anual_series.idxmax()
    max_anio_val = precip_anual_series.max()
    str_anio, str_precip = f"{max_anio}", f"{max_anio_val:,.1f} mm acumulados"
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
  st.metric(
      "Tº Máx. Absoluta",
      f"{val_tmax:.1f} °C" if pd.notnull(val_tmax) else "N/D",
      delta=f"Ocurrió el {fecha_tmax}",
      delta_color="off",
  )
with col2:
  st.metric(
      "Tº Mín. Absoluta",
      f"{val_tmin:.1f} °C" if pd.notnull(val_tmin) else "N/D",
      delta=f"Ocurrió el {fecha_tmin}",
      delta_color="off",
  )
with col3:
  st.metric(
      "Año con Mayor Precipitación",
      str_anio,
      delta=str_precip,
      delta_color="off",
  )
with col4:
  st.metric("Cantidad de Registros", f"{cant_datos:,} días")

st.markdown("---")

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Series Diarias",
    "🗓️ Comparativa ENSO / Interanual",
    "🗺️ Visor Geográfico",
    "📋 Tablas y Resúmenes",
])

# 1. SERIES DIARIAS
with tab1:
  if df_estacion.empty:
    st.warning("No hay datos disponibles para los filtros seleccionados.")
  else:
    fig_temp = go.Figure()
    fig_temp.add_trace(
        go.Scatter(
            x=df_estacion["fecha"],
            y=df_estacion["tmax"],
            mode="lines",
            name="T. Máx (°C)",
            line=dict(color="#d9534f"),
        )
    )
    fig_temp.add_trace(
        go.Scatter(
            x=df_estacion["fecha"],
            y=df_estacion["tmin"],
            mode="lines",
            name="T. Mín (°C)",
            line=dict(color="#0275d8"),
        )
    )
    fig_temp.update_layout(
        title="Temperaturas Diarias", hovermode="x unified"
    )
    st.plotly_chart(fig_temp, width="content")

    fig_precip = px.bar(
        df_estacion,
        x="fecha",
        y="precip",
        title="Precipitación Diaria (mm)",
        color_discrete_sequence=["#5bc0de"],
    )
    st.plotly_chart(fig_precip, width="content")

# 2. COMPARATIVA ENSO / INTERANUAL
with tab2:
  st.subheader("Análisis Interanual y Fases El Niño / La Niña (ENSO)")

  if df_estacion.empty:
    st.warning("No hay datos disponibles para la estación seleccionada.")
  else:
    df_enso = df_estacion.copy()
    df_enso["anio"] = df_enso["fecha"].dt.year
    df_enso["mes_num"] = df_enso["fecha"].dt.month
    df_enso["Fase_ENSO"] = df_enso["fecha"].apply(obtener_fase_enso_fecha)

    df_mensual = (
        df_enso.groupby(["anio", "mes_num", "Fase_ENSO"])["precip"]
        .sum(min_count=1)
        .reset_index()
    )
    df_mensual["anio_str"] = df_mensual["anio"].astype(str)

    fig_interanual = px.line(
        df_mensual,
        x="mes_num",
        y="precip",
        color="anio_str",
        markers=True,
        title="Precipitación Mensual por Año",
        labels={
            "mes_num": "Mes",
            "precip": "Precipitación (mm)",
            "anio_str": "Año",
        },
    )
    tick_vals = list(dict_meses.keys())
    tick_texts = [dict_meses[m][:3] for m in tick_vals]
    fig_interanual.update_layout(
        xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_texts)
    )
    st.plotly_chart(fig_interanual, width="content")

    st.markdown("---")
    st.subheader("📊 Comportamiento Medio según Fase ENOS")

    df_fases = (
        df_enso.groupby(["Fase_ENSO", "mes_num"])
        .agg({"precip": "mean", "tmax": "mean", "tmin": "mean"})
        .reset_index()
    )

    color_map_enso = {
        "El Niño": "#d9534f",
        "La Niña": "#0275d8",
        "Neutral": "#5cb85c",
    }

    col_e1, col_e2 = st.columns(2)

    with col_e1:
      fig_enso_precip = px.bar(
          df_fases,
          x="mes_num",
          y="precip",
          color="Fase_ENSO",
          barmode="group",
          color_discrete_map=color_map_enso,
          title="Precipitación Media Mensual por Fase ENOS (mm)",
          labels={
              "mes_num": "Mes",
              "precip": "Precipitación Media (mm)",
              "Fase_ENSO": "Fase",
          },
      )
      fig_enso_precip.update_layout(
          xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_texts)
      )
      st.plotly_chart(fig_enso_precip, width="content")

    with col_e2:
      fig_enso_tmax = px.line(
          df_fases,
          x="mes_num",
          y="tmax",
          color="Fase_ENSO",
          markers=True,
          color_discrete_map=color_map_enso,
          title="Tº Máxima Promedio por Fase ENOS (°C)",
          labels={
              "mes_num": "Mes",
              "tmax": "Tº Máxima (°C)",
              "Fase_ENSO": "Fase",
          },
      )
      fig_enso_tmax.update_layout(
          xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_texts)
      )
      st.plotly_chart(fig_enso_tmax, width="content")

# 3. VISOR GEOGRÁFICO
with tab3:
  st.subheader("Mapa de Ubicación de Estaciones")
  df_mapa = df_nomina_active.dropna(subset=["lat", "lon"]).copy()
  df_mapa["Estado"] = df_mapa["nombre"].apply(
      lambda x: (
          "Estación Seleccionada" if x == estacion_sel else "Otras Estaciones"
      )
  )

  fig_map = px.scatter_geo(
      df_mapa,
      lat="lat",
      lon="lon",
      hover_name="nombre",
      hover_data=["provincia", "id_estacion"],
      color="Estado",
      color_discrete_map={
          "Estación Seleccionada": "#d9534f",
          "Otras Estaciones": "#0275d8",
      },
      size=df_mapa["Estado"].apply(
          lambda x: 14 if x == "Estación Seleccionada" else 6
      ),
      scope="south america",
      center={"lat": info_estacion["lat"], "lon": info_estacion["lon"]},
      projection="mercator",
  )
  fig_map.update_layout(
      height=600,
      margin={"r": 0, "t": 10, "l": 0, "b": 0},
      geo=dict(
          showland=True,
          landcolor="rgb(243, 243, 243)",
          showcountries=True,
          countrycolor="rgb(204, 204, 204)",
          fitbounds="locations",
      ),
  )
  st.plotly_chart(fig_map, width="content")

# 4. TABLAS Y RESÚMENES
with tab4:
  subtab1, subtab2, subtab3 = st.tabs([
      "🗓️ Resumen Mensual",
      "🌧️ Precipitación Anual",
      "📄 Datos Diarios Crudos",
  ])

  if df_estacion.empty:
    st.warning("No hay datos para calcular resúmenes.")
  else:
    df_estacion_calc = df_estacion.copy()
    df_estacion_calc["tmedia"] = (
        df_estacion_calc["tmax"] + df_estacion_calc["tmin"]
    ) / 2

    with subtab1:
      st.subheader("Resumen Climatológico por Año-Mes")
      df_estacion_calc["Año_Mes"] = df_estacion_calc["fecha"].dt.to_period("M")
      resumen_mensual = []
      for periodo, group in df_estacion_calc.groupby("Año_Mes"):
        resumen_mensual.append({
            "Año-Mes": str(periodo),
            "T. Media (°C)": round(group["tmedia"].mean(), 1),
            "T. Máx. Absoluta (°C)": group["tmax"].max(),
            "T. Mín. Absoluta (°C)": group["tmin"].min(),
            "Precip. Acumulada (mm)": round(group["precip"].sum(), 1),
            "Días con Lluvia": int((group["precip"] > 0.1).sum()),
            "Cantidad de Datos": len(group),
        })
      df_resumen_m = pd.DataFrame(resumen_mensual)
      st.dataframe(df_resumen_m, width="content", hide_index=True)

    with subtab2:
      st.subheader("Precipitación Total por Año")
      df_estacion_calc["anio"] = df_estacion_calc["fecha"].dt.year
      resumen_anual = []
      for anio, group in df_estacion_calc.groupby("anio"):
        fase_rep = obtener_fase_enso_fecha(
            pd.Timestamp(year=anio, month=10, day=1)
        )
        resumen_anual.append({
            "Año": anio,
            "Fase ENOS": fase_rep,
            "Precip. Acumulada (mm)": round(group["precip"].sum(), 1),
            "Días con Precipitación (>0.1mm)": int(
                (group["precip"] > 0.1).sum()
            ),
            "Cantidad de Datos": len(group),
        })
      df_resumen_a = pd.DataFrame(resumen_anual)
      st.dataframe(df_resumen_a, width="content", hide_index=True)

    with subtab3:
      st.subheader("Registros Diarios")
      df_export = df_estacion[[
          "id_estacion",
          "nombre",
          "provincia",
          "fecha",
          "tmax",
          "tmin",
          "precip",
      ]].copy()
      df_export["fecha"] = df_export["fecha"].dt.strftime("%Y-%m-%d")
      st.dataframe(df_export, width="content", hide_index=True)
