import glob
import os
import re
import pandas as pd

# ----------------------------------------------------------------------
# 1. DEFINICIÓN DE ESTRUCTURA Y FORMATO DE ANCHO FIJO (COLSPECS)
# ----------------------------------------------------------------------
# Definimos las posiciones exactas basadas en la muestra de datos provista
ANCHO_COLUMNAS = [
    (0, 2),    # cod_interno (50)
    (2, 5),    # id_estacion (446)
    (5, 9),    # anio (2021)
    (9, 11),   # mes (02)
    (11, 13),  # dia (25)
    (13, 18),  # tmax (34.6)
    (18, 23),  # tmin (17.4)
    (23, 28),  # precip (16.5)
    (28, 33),  # cod_lluvia (19900 o 09900)
    (33, 38),  # t_005cm (16.5)
    (38, 43),  # dato_sd1 (-99.9)
    (43, 48),  # dato_sd2 (-99.9)
    (48, 53),  # dato_sd3 (-99.9)
    (53, 58),  # heliofania (8.8)
    (58, 61),  # hr (68)
    (61, 66),  # t_rocio (15.4)
    (66, 71),  # viento_10m (11.6)
    (71, 75),  # viento_2m (17)
    (75, 80),  # dato_sd4 (-99.9)
    (80, 85),  # radiacion (20.3)
    (85, 90)   # etp (6.3)
]

NOMBRES_COLUMNAS = [
    'cod_interno', 'id_estacion', 'anio', 'mes', 'dia',
    'tmax', 'tmin', 'precip', 'cod_lluvia', 't_005cm',
    'dato_sd1', 'dato_sd2', 'dato_sd3', 'heliofania',
    'hr', 't_rocio', 'viento_10m', 'viento_2m',
    'dato_sd4', 'radiacion', 'etp'
]

COLUMNAS_NUMERICAS = [
    'tmax', 'tmin', 'precip', 't_005cm', 'heliofania',
    'hr', 't_rocio', 'viento_10m', 'viento_2m', 'radiacion', 'etp'
]

# ----------------------------------------------------------------------
# 2. LECTURA Y ESCRITURA DE ARCHIVOS .DAT
# ----------------------------------------------------------------------
def cargar_dat(filepath):
    """Lee el archivo .dat usando posiciones de ancho fijo."""
    try:
        df = pd.read_fwf(
            filepath,
            colspecs=ANCHO_COLUMNAS,
            names=NOMBRES_COLUMNAS,
            dtype=str
        )
        
        # Limpiar espacios en blanco
        for col in df.columns:
            df[col] = df[col].str.strip()

        # Reemplazar valores de no dato (-99.9, -99, etc.) por NaN
        df.replace(['-99.9', '-99.0', '-999', '-9999', '-99'], pd.NA, inplace=True)

        # Convertir variables meteorológicas a numéricas
        for col in COLUMNAS_NUMERICAS + ['anio', 'mes', 'dia']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df
    except Exception as e:
        print(f"❌ Error al leer el archivo {filepath}: {e}")
        return None

def guardar_dat(df, filepath_destino):
    """Guarda el DataFrame restaurando el formato original de cadenas sin perder datos."""
    lines = []
    for _, r in df.iterrows():
        # Formateo auxiliar para variables numéricas
        def fmt(val, width, dec=1):
            if pd.isna(val) or val is None:
                return "-99.9".rjust(width)
            return f"{float(val):.{dec}f}".rjust(width)

        # Reconstrucción línea a línea con anchos exactos
        linea = (
            f"{int(r['cod_interno']):02d}"
            f"{int(r['id_estacion']):03d}"
            f"{int(r['anio']):04d}"
            f"{int(r['mes']):02d}"
            f"{int(r['dia']):02d}"
            f"{fmt(r['tmax'], 5)}"
            f"{fmt(r['tmin'], 5)}"
            f"{fmt(r['precip'], 5)}"
            f"{str(r['cod_lluvia']).strip().rjust(5)}"
            f"{fmt(r['t_005cm'], 5)}"
            f"{'-99.9'.rjust(5)}"
            f"{'-99.9'.rjust(5)}"
            f"{'-99.9'.rjust(5)}"
            f"{fmt(r['heliofania'], 5)}"
            f"{int(r['hr']) if pd.notnull(r['hr']) else -99:3d}"
            f"{fmt(r['t_rocio'], 5)}"
            f"{fmt(r['viento_10m'], 5)}"
            f"{fmt(r['viento_2m'], 4, dec=0)}"
            f"{'-99.9'.rjust(5)}"
            f"{fmt(r['radiacion'], 5)}"
            f"{fmt(r['etp'], 5)}"
        )
        lines.append(linea)

    os.makedirs(os.path.dirname(filepath_destino), exist_ok=True)
    with open(filepath_destino, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"💾 Archivo guardado correctamente en: {filepath_destino}")

# ----------------------------------------------------------------------
# 3. CONTROL DE CALIDAD (QC)
# ----------------------------------------------------------------------
def validar_fila(row, prev_row=None, next_row=None):
    errores = []
    tmax, tmin, precip = row['tmax'], row['tmin'], row['precip']

    # Rangos absolutos
    if pd.notnull(tmax) and (tmax < -30 or tmax > 55):
        errores.append(f"TMAX fuera de rango: {tmax} °C")
    if pd.notnull(tmin) and (tmin < -25 or tmin > 35):
        errores.append(f"TMIN fuera de rango: {tmin} °C")
    if pd.notnull(precip) and (precip < 0 or precip > 300):
        errores.append(f"PRECIP fuera de rango: {precip} mm")

    # Incoherencia TMIN > TMAX
    if pd.notnull(tmax) and pd.notnull(tmin) and tmin > tmax:
        errores.append(f"Incoherencia TMIN > TMAX: TMIN={tmin}°C, TMAX={tmax}°C")

    # Saltos térmicos abruptos respecto al día anterior
    if prev_row is not None:
        if pd.notnull(tmin) and pd.notnull(prev_row['tmin']):
            if abs(tmin - prev_row['tmin']) > 12.0:
                errores.append(f"Salto abrupto de TMIN: {prev_row['tmin']}°C -> {tmin}°C")
        if pd.notnull(tmax) and pd.notnull(prev_row['tmax']):
            if abs(tmax - prev_row['tmax']) > 15.0:
                errores.append(f"Salto abrupto de TMAX: {prev_row['tmax']}°C -> {tmax}°C")

    return errores

# ----------------------------------------------------------------------
# 4. AUDITORÍA INTERACTIVA
# ----------------------------------------------------------------------
def auditar_estacion(filepath, output_dir):
    nombre_archivo = os.path.basename(filepath)
    print(f"\n==========================================")
    print(f"📂 Auditando: {nombre_archivo}")
    print(f"==========================================")

    df = cargar_dat(filepath)
    if df is None or df.empty:
        return

    modificado = False
    n_filas = len(df)

    for i in range(n_filas):
        row = df.iloc[i]
        prev_row = df.iloc[i - 1] if i > 0 else None
        next_row = df.iloc[i + 1] if i < n_filas - 1 else None

        errores = validar_fila(row, prev_row, next_row)

        if errores:
            fecha_str = f"{int(row['dia']):02d}/{int(row['mes']):02d}/{int(row['anio'])}"
            print("\n" + "!" * 65)
            print(f"⚠️ ANOMALÍA DETECTADA en Fila {i+1} | Fecha: {fecha_str}")
            for err in errores:
                print(f"   ↳ {err}")
            print("-" * 65)

            # Ventana contextual
            idx_inicio = max(0, i - 2)
            idx_fin = min(n_filas, i + 3)
            contexto = df.iloc[idx_inicio:idx_fin].copy()
            contexto['FECHA'] = contexto.apply(
                lambda r: f"{int(r['dia']):02d}/{int(r['mes']):02d}/{int(r['anio'])}", axis=1
            )
            print(contexto[['FECHA', 'tmax', 'tmin', 'precip', 'etp']].to_string(index=False))
            print("-" * 65)

            while True:
                accion = input("¿Qué querés hacer? [c]orregir / [o]mitir / [m]antener: ").strip().lower()

                if accion == 'c':
                    var = input("¿Qué variable corregir? (tmax/tmin/precip/etp/hr/viento_10m): ").strip().lower()
                    if var in df.columns:
                        nuevo_val_str = input(f"Nuevo valor para {var.upper()}: ").strip()
                        try:
                            df.at[i, var] = float(nuevo_val_str)
                            modificado = True
                            print(f"✅ Correcto: {var.upper()} en {fecha_str} cambiado a {nuevo_val_str}")
                            break
                        except ValueError:
                            print("❌ Valor no válido.")
                    else:
                        print("❌ Variable no válida.")

                elif accion == 'o':
                    var = input("¿Qué variable anular/setear como dato faltante? (o 'todas'): ").strip().lower()
                    if var in df.columns:
                        df.at[i, var] = pd.NA
                        modificado = True
                        break
                    elif var == 'todas':
                        for c in COLUMNAS_NUMERICAS:
                            df.at[i, c] = pd.NA
                        modificado = True
                        break

                elif accion == 'm':
                    print("⏩ Se mantiene el valor original.")
                    break

    # Guardado automático al terminar la revisión de la estación
    filepath_destino = os.path.join(output_dir, nombre_archivo)
    if modificado:
        guardar_dat(df, filepath_destino)
    else:
        # Guardar copia limpia incluso si no fue modificado
        guardar_dat(df, filepath_destino)

# ----------------------------------------------------------------------
# 5. EJECUCIÓN PRINCIPAL
# ----------------------------------------------------------------------
def procesar_directorio(carpeta_origen, carpeta_destino):
    archivos = glob.glob(os.path.join(carpeta_origen, "*.dat"))
    if not archivos:
        print(f"No se encontraron archivos .dat en '{carpeta_origen}'")
        return

    print(f"Se encontraron {len(archivos)} archivos .dat en {carpeta_origen}.")
    for filepath in archivos:
        auditar_estacion(filepath, carpeta_destino)

if __name__ == "__main__":
    subcarpetas = ["smn", "ema", "inta"]
    base_origen = "."  # Ejecutando desde dentro de C:\Depaso\datos_crudos
    base_destino = "../datos_limpios"

    for sub in subcarpetas:
        origen = os.path.join(base_origen, sub)
        destino = os.path.join(base_destino, sub)

        print(f"\n==========================================")
        print(f"📁 PROCESANDO CATEGORÍA: {sub.upper()}")
        print(f"==========================================")

        procesar_directorio(origen, destino)