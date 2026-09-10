import pandas as pd
import os

print("🔄 Generando estaciones.parquet desde nomina_estaciones.csv...")

archivo_csv = "nomina_estaciones.csv"

if not os.path.exists(archivo_csv):
    raise FileNotFoundError(f"No se encontró el archivo '{archivo_csv}'.")

# 1. Leer la nómina unificada manejando caracteres especiales de Windows
try:
    df_nomina = pd.read_csv(archivo_csv, encoding="utf-8")
except UnicodeDecodeError:
    df_nomina = pd.read_csv(archivo_csv, encoding="latin1")

# 2. Normalizar nombres de columnas a minúsculas sin espacios
df_nomina.columns = df_nomina.columns.str.lower().str.strip()

# 3. Formatear id_estacion como texto uniforme de 5 dígitos
if 'id_estacion' in df_nomina.columns:
    df_nomina['id_estacion'] = df_nomina['id_estacion'].astype(str).str.zfill(5)

# 4. Asegurar que 'provincia' exista y optimizar tipos de datos para Streamlit
if 'provincia' in df_nomina.columns:
    df_nomina['provincia'] = df_nomina['provincia'].fillna('SIN ASIGNAR').astype('category')

if 'nombre' in df_nomina.columns:
    df_nomina['nombre'] = df_nomina['nombre'].fillna('Desconocida')

# 5. Exportar a Parquet
df_nomina.to_parquet("estaciones.parquet", index=False)

print("✅ Archivo 'estaciones.parquet' creado exitosamente.")
print("📌 Columnas en estaciones.parquet:", df_nomina.columns.tolist())