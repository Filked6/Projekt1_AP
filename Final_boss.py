import arcpy
from arcpy.sa import *
import os

from dask.bag.core import accumulate_part

########################
# Zmienne środowiskowe #
########################
arcpy.env.workspace = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Projekt1_AP.gdb"
arcpy.env.overwriteOutput = True
arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(2180)
arcpy.env.cellSize = 10

#################################
# Ścieżki do danych do projektu #
#################################
bdot10k_data = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\3214_SHP"
acceptable_file_names = ("budynek", "drogi", "lasy", "rezerwat1", "rezerwat2", "woda", "rzeka")

project_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Projekt1_AP.aprx"
aprx = arcpy.mp.ArcGISProject(project_path)

###########
# Funkcje #
###########
def import_shp_to_gdb(shp_folder, gdb, startings):
    folder = os.listdir(shp_folder)
    for shp in folder:
        if shp.startswith(startings) and shp.endswith(".shp"):
            full_path = os.path.join(shp_folder, shp)

            out_name = os.path.splitext(shp)[0]
            out_path = os.path.join(gdb, out_name)

            print(f"Importuję do GDB: {shp} -> {out_name}")
            arcpy.management.CopyFeatures(full_path, out_path)

#####################
# Wywołania funkcji #
#####################
#Tą funkcję się uruchamia tylko za pierwszym razem, gdy nie mamy plików shp w geobazie
#import_shp_to_gdb(bdot10k_data, arcpy.env.workspace, acceptable_file_names)