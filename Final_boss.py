import arcpy
from arcpy.sa import *
import os

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
project_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Projekt1_AP.aprx"
acceptable_file_names = ("budynek", "drogi", "lasy", "rezerwat1", "rezerwat2", "woda", "rzeka")

aprx = arcpy.mp.ArcGISProject(project_path)
mapa = aprx.listMaps()[0]

###########
# Funkcje #
###########
def add_shp_files_to_arcgis(shp_folder, mapp, startings):
    folder = os.listdir(shp_folder)
    for shp in folder:
        if shp.lower().startswith(startings) and shp.endswith(".shp"):
            full_path = os.path.join(shp_folder, shp)
            print(f"Dodaję: {shp}")
            mapp.addDataFromPath(full_path)

    aprx.save()

#####################
# Wywołania funkcji #
#####################
#Tą funkcję się uruchamia tylko za pierwszym razem, gdy nie mamy plików shp w ArcGisie
#add_shp_files_to_arcgis(bdot10k_data, mapa, acceptable_file_names)