import os
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="Visor Climatológico - Argentina", page_icon="🌤️", layout="wide"
)

# Estilos CSS personalizados para Tarjetas KPI
st.markdown(
    """
<style>
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #007bff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 0.85rem;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: bold;
        color: #212529;
        margin: 5px 0;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #495057;
    }
</style>
""",
    unsafe_allow_html=True,
)


def limpiar_id(val):
  if pd.isna(val):
    return ""
  val_str = str(val).strip().upper()
  digitos = re.sub(r"\D", "", val_str)
  return digitos if digitos else val_str


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


def obtener_fase_enso_anio(anio):
  ciclo = f"{anio}-{anio + 1}"
  return TABLA_ENSO.get(ciclo, "Neutral")


@st.cache_data
def load_data():
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

  # Normalización defensiva del campo 'nombre'
  renom_nomina = {
      "localidad": "nombre",
      "estacion": "nombre",
      "latitud": "lat",
      "longitud": "lon",
      "altitud": "altura",
  }
  df_nomina_conv = df_nomina_conv.rename(
      columns={
          k: v for k, v in renom_nomina.items() if k in df_nomina_conv.columns
      }
  )

  if "provincia" not in df_nomina_conv.columns:
    df_nomina_conv["provincia"] = "Sin Especificar"

  for col in ["nombre", "provincia"]:
    if col in df_conv.columns:
      df_conv = df_conv.drop(columns=[col])

  cols_merge_conv = [
      c
      for c in ["id_estacion", "nombre", "provincia", "lat", "lon", "altura"]
      if c in df_nomina_conv.columns
  ]
  df_conv = df_conv.merge(
      df_nomina_conv[cols_merge_conv], on="id_estacion", how="left"
  )

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
      elif col_lower in ["nombre", "localidad", "estacion"]:
        renombrar_dict[col] = "nombre"
      elif col_lower == "provincia":
        renombrar_dict[col] = "provincia"
      elif col_lower in ["latitud", "lat"]:
        renombrar_dict[col] = "lat"
      elif col_lower in ["longitud", "lon"]:
        renombrar_dict[col] = "lon"

    df_nomina_emas = df_nomina_emas.rename(columns=renombrar_dict)
    df_nomina_emas["id_estacion"] = df_nomina_emas["id_estacion"].apply(
        limpiar_id
    )

    if "nombre" not in df_nomina_emas.columns:
      df_nomina_emas["nombre"] = df_nomina_emas["id_estacion"]
    if "provincia" not in df_nomina_emas.columns:
      df_nomina_emas["provincia"] = "Sin Especificar"
    if "altura" not in df_nomina_emas.columns:
      df_nomina_emas["altura"] = 0

  if os.path.exists("estaciones_automaticas.parquet"):
    df_auto = pd.read_parquet("estaciones_automaticas.parquet")

    if "Id" in df_auto.columns:
      df_auto = df_auto.rename(columns={"Id": "id_estacion"})

    df_auto["id_estacion"] = df_auto["id_estacion"].apply(limpiar_id)
    df_auto["fecha"] = pd.to_datetime(df_auto["fecha"])

    for col in ["nombre", "provincia"]:
      if col in df_auto.columns:
        df_auto = df_auto.drop(columns=[col])

    if not df_nomina_emas.empty:
      cols_merge_emas = [
          c
          for c in ["id_estacion", "nombre", "provincia", "lat", "lon", "altura"]
          if c in df_nomina_emas.columns
      ]
      df_auto = df_auto.merge(
          df_nomina_emas[cols_merge_emas], on="id_estacion", how="left"
      )

  return df_conv, df_nomina_conv, df_auto, df_nomina_emas


try:
  df_conv, df_nomina_conv, df_auto, df_nomina_emas = load_data()
except Exception as e:
  st.error(f"Error al cargar datos: {e}")
  st.stop()

# --- FILTROS LATERALES ---
st.sidebar.title("🎛️ Filtros y Opciones")

tipo_red = st.sidebar.radio(
    "Red de Estaciones", ["Convencionales (SMN / INTA)", "Automáticas (EMAS)"]
)

if tipo_red == "Convencionales (SMN / INTA)":
  df_active, df_nomina_active = df_conv, df_nomina_conv
else:
  df_active, df_nomina_active = df_auto, df_nomina_emas
  if df_active.empty:
    st.sidebar.warning("No hay datos en estaciones automáticas.")
    st.stop()

provincias = ["Todas"] + sorted(
    df_nomina_active["provincia"].dropna().unique().tolist()
)
prov_sel = st.sidebar.selectbox("Provincia", provincias)

df_nomina_filtrada = (
    df_nomina_active[df_nomina_active["provincia"] == prov_sel]
    if prov_sel != "Todas"
    else df_nomina_active
)
estaciones = sorted(df_nomina_filtrada["nombre"].dropna().unique().tolist())

if not estaciones:
  st.sidebar.warning("No hay estaciones disponibles.")
  st.stop()

estacion_sel = st.sidebar.selectbox("Estación", estaciones)

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

# Filtro de Meses
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
  for m in dict_meses:
    st.session_state[f"chk_mes_{m}"] = True


def toggle_meses():
  st_val = st.session_state["todos_meses"]
  for m in dict_meses:
    st.session_state[f"chk_mes_{m}"] = st_val


st.sidebar.checkbox(
    "Seleccionar Todos los Meses", key="todos_meses", on_change=toggle_meses
)
meses_sel = []
with st.sidebar.expander("Filtrar Meses", expanded=False):
  c1, c2 = st.columns(2)
  for num_m, nom_m in dict_meses.items():
    col = c1 if num_m % 2 != 0 else c2
    if col.checkbox(nom_m, key=f"chk_mes_{num_m}"):
      meses_sel.append(num_m)

if not meses_sel:
  st.warning("Por favor seleccioná al menos un mes.")
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

df_estacion_historico = df_active[
    df_active["id_estacion"] == id_estacion_sel
].copy()

df_estacion = df_estacion_historico[
    (df_estacion_historico["fecha"].dt.date >= fecha_inicio)
    & (df_estacion_historico["fecha"].dt.date <= fecha_fin)
    & (df_estacion_historico["fecha"].dt.month.isin(meses_sel))
].sort_values("fecha")

# --- ENCABEZADO Y TARJETAS KPI ---
st.title(f"📊 {info_estacion['nombre']}")
alt_val = info_estacion.get("altura", "N/D")
st.caption(
    f"**Red:** {tipo_red} | **Provincia:** {info_estacion['provincia']} | **ID:**"
    f" {id_estacion_sel} | **Altitud:** {alt_val} msnm"
)

if not df_estacion.empty:
  idx_tmax = (
      df_estacion["tmax"].idxmax()
      if df_estacion["tmax"].notnull().any()
      else None
  )
  val_tmax = (
      df_estacion.loc[idx_tmax, "tmax"] if idx_tmax is not None else None
  )
  f_tmax = (
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
  f_tmin = (
      df_estacion.loc[idx_tmin, "fecha"].strftime("%d/%m/%Y")
      if idx_tmin is not None
      else "N/D"
  )

  df_estacion_temp = df_estacion.copy()
  df_estacion_temp["anio"] = df_estacion_temp["fecha"].dt.year
  precip_anual_calc = (
      df_estacion_temp.groupby("anio")["precip"].sum(min_count=1).dropna()
  )

  if not precip_anual_calc.empty:
    anio_max_p = precip_anual_calc.idxmax()
    val_max_p = precip_anual_calc.max()
    sub_max_p = f"{val_max_p:,.1f} mm acumulados"
    val_max_p_str = f"{anio_max_p}"
  else:
    val_max_p_str = "N/D"
    sub_max_p = "Sin datos"

  k1, k2, k3, k4 = st.columns(4)

  with k1:
    st.markdown(
        f"""<div class="kpi-card" style="border-left-color: #dc3545;">
            <div class="kpi-title">Tº Máx. Absoluta</div>
            <div class="kpi-value">{f'{val_tmax:.1f} °C' if val_tmax else 'N/D'}</div>
            <div class="kpi-sub">📅 {f_tmax}</div>
        </div>""",
        unsafe_allow_html=True,
    )

  with k2:
    st.markdown(
        f"""<div class="kpi-card" style="border-left-color: #0d6efd;">
            <div class="kpi-title">Tº Mín. Absoluta</div>
            <div class="kpi-value">{f'{val_tmin:.1f} °C' if val_tmin else 'N/D'}</div>
            <div class="kpi-sub">📅 {f_tmin}</div>
        </div>""",
        unsafe_allow_html=True,
    )

  with k3:
    st.markdown(
        f"""<div class="kpi-card" style="border-left-color: #198754;">
            <div class="kpi-title">Año Máx. Precipitación</div>
            <div class="kpi-value">{val_max_p_str}</div>
            <div class="kpi-sub">🌧️ {sub_max_p}</div>
        </div>""",
        unsafe_allow_html=True,
    )

  with k4:
    st.markdown(
        f"""<div class="kpi-card" style="border-left-color: #6c757d;">
            <div class="kpi-title">Registros Eval.</div>
            <div class="kpi-value">{len(df_estacion):,}</div>
            <div class="kpi-sub">Días observados en el rango</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("---")

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Series Diarias y Climatología",
    "🗓️ ENSO y Mapa Interanual",
    "🗺️ Visor Geográfico",
    "📋 Tablas y Resúmenes",
])

# 1. SERIES DIARIAS Y CLIMATOLOGÍA
with tab1:
  if df_estacion.empty:
    st.warning("No hay registros para la selección actual.")
  else:
    df_estacion_historico["dia_mes"] = df_estacion_historico[
        "fecha"
    ].dt.strftime("%m-%d")

    clim_tmax = df_estacion_historico.groupby("dia_mes")["tmax"].mean()
    clim_tmin = df_estacion_historico.groupby("dia_mes")["tmin"].mean()

    df_estacion["dia_mes"] = df_estacion["fecha"].dt.strftime("%m-%d")
    df_estacion["tmax_clim"] = df_estacion["dia_mes"].map(clim_tmax)
    df_estacion["tmin_clim"] = df_estacion["dia_mes"].map(clim_tmin)

    # Gráfico Tmax
    fig_tmax = go.Figure()
    fig_tmax.add_trace(
        go.Scatter(
            x=df_estacion["fecha"],
            y=df_estacion["tmax"],
            mode="lines",
            name="T° Máxima Diaria",
            line=dict(color="#dc3545", width=1.8),
        )
    )
    fig_tmax.add_trace(
        go.Scatter(
            x=df_estacion["fecha"],
            y=df_estacion["tmax_clim"],
            mode="lines",
            name="Media Climatológica T° Máx",
            line=dict(color="#6c757d", width=2, dash="dash"),
        )
    )
    fig_tmax.update_layout(
        title="Evolución de Temperatura Máxima Diaria vs. Media Climatológica",
        hovermode="x unified",
        yaxis_title="Temperatura (°C)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_tmax, use_container_width=True)

    # Gráfico Tmin
    fig_tmin = go.Figure()
    fig_tmin.add_trace(
        go.Scatter(
            x=df_estacion["fecha"],
            y=df_estacion["tmin"],
            mode="lines",
            name="T° Mínima Diaria",
            line=dict(color="#0d6efd", width=1.8),
        )
    )
    fig_tmin.add_trace(
        go.Scatter(
            x=df_estacion["fecha"],
            y=df_estacion["tmin_clim"],
            mode="lines",
            name="Media Climatológica T° Mín",
            line=dict(color="#6c757d", width=2, dash="dash"),
        )
    )
    fig_tmin.update_layout(
        title="Evolución de Temperatura Mínima Diaria vs. Media Climatológica",
        hovermode="x unified",
        yaxis_title="Temperatura (°C)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_tmin, use_container_width=True)

    # Gráfico Precipitación Diaria
    fig_precip = go.Figure()
    fig_precip.add_trace(
        go.Bar(
            x=df_estacion["fecha"],
            y=df_estacion["precip"],
            name="Precipitación Diaria (mm)",
            marker_color="#0dcaf0",
            opacity=0.8,
        )
    )
    fig_precip.update_layout(
        title="Precipitación Diaria",
        hovermode="x unified",
        yaxis_title="Lluvia Diaria (mm)",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig_precip, use_container_width=True)

# 2. ENSO Y MAPA INTERANUAL POR AÑO
with tab2:
  st.subheader("Análisis Interanual y Fases ENSO (El Niño / La Niña / Neutral)")

  if not df_estacion.empty:
    df_enso = df_estacion.copy()
    df_enso["anio"] = df_enso["fecha"].dt.year
    df_enso["mes_num"] = df_enso["fecha"].dt.month
    df_enso["Fase_ENSO"] = df_enso["fecha"].apply(obtener_fase_enso_fecha)
    df_enso["Año_Fase"] = (
        df_enso["anio"].astype(str) + " (" + df_enso["Fase_ENSO"] + ")"
    )

    # --- PRECIPITACIÓN TOTAL ANUAL SEGÚN FASE ENSO (ORDENADO CRONOLÓGICAMENTE) ---
    df_precip_anual = (
        df_enso.groupby(["anio", "Fase_ENSO"])["precip"]
        .sum(min_count=1)
        .reset_index()
        .sort_values("anio", ascending=True)
    )

    df_precip_anual["anio_str"] = df_precip_anual["anio"].astype(str)
    anios_ordenados_str = df_precip_anual["anio_str"].unique().tolist()

    fig_precip_enso = px.bar(
        df_precip_anual,
        x="anio_str",
        y="precip",
        color="Fase_ENSO",
        title="Precipitación Total Anual según Clasificación ENSO (Orden Cronológico)",
        labels={
            "anio_str": "Año",
            "precip": "Precipitación Acumulada (mm)",
            "Fase_ENSO": "Fase ENSO",
        },
        color_discrete_map={
            "El Niño": "#dc3545",
            "La Niña": "#0d6efd",
            "Neutral": "#28a745",
        },
    )
    fig_precip_enso.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=anios_ordenados_str,
        )
    )
    st.plotly_chart(fig_precip_enso, use_container_width=True)

    st.markdown("---")

    # --- GRÁFICO DE EVOLUCIÓN MENSUAL COMPARATIVA POR AÑO Y FASE ENSO ---
    var_enso = st.selectbox(
        "Seleccioná la variable a comparar por año y Fase ENSO:",
        [
            "Precipitación (mm)",
            "Temperatura Máxima (°C)",
            "Temperatura Mínima (°C)",
        ],
    )

    if var_enso == "Precipitación (mm)":
      df_m = (
          df_enso.groupby(["anio", "Año_Fase", "mes_num"])["precip"]
          .sum(min_count=1)
          .reset_index()
      )
      col_y = "precip"
      title_y = "Lluvia Acumulada Mensual (mm)"
    elif var_enso == "Temperatura Máxima (°C)":
      df_m = (
          df_enso.groupby(["anio", "Año_Fase", "mes_num"])["tmax"]
          .mean()
          .reset_index()
      )
      col_y = "tmax"
      title_y = "T° Máxima Promedio Mensual (°C)"
    else:
      df_m = (
          df_enso.groupby(["anio", "Año_Fase", "mes_num"])["tmin"]
          .mean()
          .reset_index()
      )
      col_y = "tmin"
      title_y = "T° Mínima Promedio Mensual (°C)"

    # Orden cronológico estricto (de más viejo a más reciente)
    df_m = df_m.sort_values(["anio", "mes_num"], ascending=[True, True])
    orden_anos_fase = (
        df_m[["anio", "Año_Fase"]].drop_duplicates().sort_values("anio")["Año_Fase"].tolist()
    )

    fig_interanual = px.line(
        df_m,
        x="mes_num",
        y=col_y,
        color="Año_Fase",
        category_orders={"Año_Fase": orden_anos_fase},
        markers=True,
        title=f"Evolución Mensual Comparativa por Año y Fase ENSO - {var_enso}",
        labels={
            "mes_num": "Mes",
            col_y: title_y,
            "Año_Fase": "Año (Fase ENSO)",
        },
    )
    t_vals = list(dict_meses.keys())
    t_text = [dict_meses[m][:3] for m in t_vals]
    fig_interanual.update_layout(
        xaxis=dict(tickmode="array", tickvals=t_vals, ticktext=t_text),
        hovermode="x unified",
    )
    st.plotly_chart(fig_interanual, use_container_width=True)

  st.markdown("---")
  st.subheader("🗺️ Mapa Interanual por Estación catalogado por Fase ENSO")

  df_map_active = df_active.copy()
  df_map_active["anio"] = df_map_active["fecha"].dt.year
  df_map_active["Fase_ENSO"] = df_map_active["fecha"].apply(
      obtener_fase_enso_fecha
  )

  df_map_anual = (
      df_map_active.groupby(["id_estacion", "anio", "Fase_ENSO"])[
          ["precip", "tmax", "tmin"]
      ]
      .agg({"precip": "sum", "tmax": "mean", "tmin": "mean"})
      .reset_index()
      .sort_values("anio", ascending=True)
  )

  cols_map_merge = [
      c
      for c in ["id_estacion", "nombre", "provincia", "lat", "lon"]
      if c in df_nomina_active.columns
  ]
  df_map_anual = df_map_anual.merge(
      df_nomina_active[cols_map_merge], on="id_estacion", how="inner"
  ).dropna(subset=["lat", "lon"])

  if not df_map_anual.empty:
    df_map_anual["Año_Str"] = df_map_anual["anio"].astype(str)

    fig_enso_map = px.scatter_geo(
        df_map_anual,
        lat="lat",
        lon="lon",
        color="Fase_ENSO",
        size="precip",
        hover_name="nombre",
        hover_data={
            "provincia": True,
            "Fase_ENSO": True,
            "anio": True,
            "precip": ":.1f",
            "tmax": ":.1f",
            "tmin": ":.1f",
            "lat": False,
            "lon": False,
        },
        animation_frame="anio",
        scope="south america",
        title="Clasificación de Fase ENSO y Precipitación Anual por Estación",
        color_discrete_map={
            "El Niño": "#dc3545",
            "La Niña": "#0d6efd",
            "Neutral": "#28a745",
        },
        labels={
            "Fase_ENSO": "Fase ENSO",
            "precip": "Precip. Acumulada (mm)",
            "tmax": "T° Máx Prom (°C)",
            "tmin": "T° Mín Prom (°C)",
            "anio": "Año",
        },
    )

    fig_enso_map.update_geos(
        showsubunits=True,
        subunitcolor="#6c757d",
        subunitwidth=1,
        showcountries=True,
        countrycolor="#343a40",
        countrywidth=1.5,
        showcoastlines=True,
        showland=True,
        landcolor="#f8f9fa",
        fitbounds="locations",
    )
    fig_enso_map.update_layout(
        height=600, margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )
    st.plotly_chart(fig_enso_map, use_container_width=True)

# 3. VISOR GEOGRÁFICO
with tab3:
  st.subheader("Ubicación Geográfica de Estaciones")
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
          "Estación Seleccionada": "#dc3545",
          "Otras Estaciones": "#0d6efd",
      },
      scope="south america",
      center={"lat": info_estacion["lat"], "lon": info_estacion["lon"]},
      projection="mercator",
  )

  fig_map.update_geos(
      showsubunits=True,
      subunitcolor="#6c757d",
      subunitwidth=1.2,
      showcountries=True,
      countrycolor="#343a40",
      countrywidth=1.5,
      showcoastlines=True,
      coastlinecolor="#343a40",
      showland=True,
      landcolor="#f8f9fa",
      fitbounds="locations",
  )

  fig_map.update_layout(
      height=550, margin={"r": 0, "t": 10, "l": 0, "b": 0}
  )
  st.plotly_chart(fig_map, use_container_width=True)

# 4. TABLAS Y RESÚMENES (CON EXPORTACIÓN A CSV)
with tab4:
  st.subheader("📋 Resúmenes y Datos de la Estación")

  if df_estacion.empty:
    st.warning("No hay registros para la selección actual.")
  else:
    df_tab = df_estacion.copy()
    df_tab["anio"] = df_tab["fecha"].dt.year
    df_tab["mes"] = df_tab["fecha"].dt.month
    df_tab["nombre_mes"] = df_tab["mes"].map(dict_meses)

    # --- TABLA 1: RESUMEN MENSUAL ---
    st.markdown("### 📊 1. Resumen Mensual")
    resumen_mensual = (
        df_tab.groupby(["anio", "mes", "nombre_mes"])
        .agg(
            tmax_promedio=("tmax", "mean"),
            tmax_absoluta=("tmax", "max"),
            tmin_promedio=("tmin", "mean"),
            tmin_absoluta=("tmin", "min"),
            precip_acumulada=("precip", "sum"),
            dias_con_lluvia=("precip", lambda x: (x > 0.1).sum()),
        )
        .reset_index()
    )

    st.dataframe(resumen_mensual, use_container_width=True, hide_index=True)
    csv_mensual = resumen_mensual.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Resumen Mensual (CSV)",
        data=csv_mensual,
        file_name=f"resumen_mensual_{id_estacion_sel}.csv",
        mime="text/csv",
        key="btn_csv_mensual",
    )

    st.markdown("---")

    # --- TABLA 2: PRECIPITACIÓN ANUAL ---
    st.markdown("### 🌧️ 2. Resumen de Precipitación Anual")
    precip_anual_tabla = (
        df_tab.groupby("anio")
        .agg(
            precip_acumulada=("precip", "sum"),
            dias_con_lluvia=("precip", lambda x: (x > 0.1).sum()),
            max_lluvia_diaria=("precip", "max"),
        )
        .reset_index()
    )

    st.dataframe(precip_anual_tabla, use_container_width=True, hide_index=True)
    csv_anual = precip_anual_tabla.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Precipitación Anual (CSV)",
        data=csv_anual,
        file_name=f"precipitacion_anual_{id_estacion_sel}.csv",
        mime="text/csv",
        key="btn_csv_anual",
    )

    st.markdown("---")

    # --- TABLA 3: DATOS DIARIOS CRUDOS ---
    st.markdown("### 📄 3. Registros Diarios Crudos")
    df_export_diarios = df_estacion.drop(
        columns=[
            "dia_mes",
            "tmax_clim",
            "tmin_clim",
            "precip_acum",
            "anio",
            "mes",
            "nombre_mes",
        ],
        errors="ignore",
    )

    st.dataframe(df_export_diarios, use_container_width=True, hide_index=True)
    csv_diarios = df_export_diarios.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Datos Diarios Crudos (CSV)",
        data=csv_diarios,
        file_name=f"datos_diarios_{id_estacion_sel}.csv",
        mime="text/csv",
        key="btn_csv_diarios",
    )
