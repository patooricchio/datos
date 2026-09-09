import pandas as pd
import geopandas as gpd

def cargar_nomina(path_archivo):
    """
    Carga la nómina desde Excel (.xlsx) o Shapefile (.shp)
    y formatea el ID de estación para hacer match con los archivos .dat.
    """
    if path_archivo.endswith('.shp'):
        gdf = gpd.read_file(path_archivo)
        df_meta = pd.DataFrame(gdf.drop(columns='geometry'))
    else:
        df_meta = pd.read_excel(path_archivo)
    
    # Formatear codigo_nh a 5 dígitos agregando el prefijo 50 para SMN
    df_meta['id_estacion'] = df_meta['codigo_nh'].apply(lambda x: f"50{int(x):03d}")
    
    return df_meta