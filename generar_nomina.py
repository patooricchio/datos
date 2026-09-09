import pandas as pd

# Cargar la tabla original de estaciones
df = pd.read_csv("estaciones_smn-inta_conv.csv")

# Generar identificador de 5 dígitos para cruce con los datos .parquet
df["id_estacion"] = df["codigo_nh"].apply(lambda x: f"50{int(x):03d}")

# Mapear columnas para asegurar compatibilidad total con Streamlit / Plotly
df["nombre"] = df["localidad"]
df["lat"] = df["latitud"]
df["lon"] = df["longitud"]
df["altura"] = df["altitud"]

# Guardar nómina optimizada
df.to_csv("nomina_estaciones.csv", index=False)
print(f"✅ 'nomina_estaciones.csv' generado correctamente ({len(df)} registros).")