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

def distance_from_water_raster(min_val = 100, mean_val = 300, max_val = 1000):
    river = "rzeka"
    water = "woda"
    river_a = arcpy.analysis.Buffer(river, "rzeka_a", "2 Meters")
    water_all = arcpy.management.Merge([river_a, water], "woda_cala")
    distance_raster = DistanceAccumulation(water_all)
    distance_raster.save("distance_raster")

    f = FuzzyLinear(max_val, mean_val)
    temp_fuzzy_raster = FuzzyMembership(distance_raster, f)

    distance_raster_final = Con(distance_raster < min_val, 0, temp_fuzzy_raster)
    distance_raster_final.save("distance_raster_water")

    #Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("woda_cala")
    arcpy.management.Delete("rzeka_a")
    arcpy.management.Delete("distance_raster")

def distance_from_buildings_raster(min_from_building = 150, better = 1500 ):
    buildings = "budynek"

    condition = "\"FOBUD\" = 'budynki mieszkalne'"
    residental = arcpy.analysis.Select(buildings, "mieszkalne", condition)
    distance_raster = DistanceAccumulation(residental)
    distance_raster.save("distance_raster_temp")

    f = FuzzyLinear(min_from_building, better)
    fuzzy_raster = FuzzyMembership(distance_raster, f)
    fuzzy_raster.save("distance_raster_residental")

    #Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("mieszkalne")
    arcpy.management.Delete("distance_raster_temp")

def distance_from_forest_raster(min_from_forest = 15, better = 100):
    forest = "lasy"
    protected1 = "rezerwat1"
    protected2 = "rezerwat2"

    land_cover = arcpy.management.Merge([forest, protected1, protected2], "pokrycie_cale")
    distance_raster = DistanceAccumulation(land_cover)
    distance_raster.save("distance_raster_land_cover_temp")

    f = FuzzyLinear(min_from_forest, better)
    fuzzy_raster = FuzzyMembership(distance_raster, f)
    fuzzy_raster.save("distance_raster_land_cover")

    # Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("pokrycie_cale")
    arcpy.management.Delete("distance_raster_land_cover_temp")

def road_availability():
    road = "drogi"
    column_values1 = ["żwir", "tłuczeń"]
    column_values2 = ["kostka kamienna", "bruk", "kostka prefabrykowana"]

    column_names = [f.name.upper() for f in arcpy.ListFields(road)]
    if "POPULATION" not in column_names:
        arcpy.management.AddField(road,"POPULATION", "SHORT")
        with arcpy.da.UpdateCursor(road, ["MATE_NAWIE", "POPULATION"]) as cursor:
            for row in cursor:
                material = row[0]
                if material is None:
                    row[1] = 0
                elif material == "grunt naturalny":
                    row[1] = 0
                elif material in column_values1:
                    row[1] = 1
                elif material in column_values2:
                    row[1] = 2
                else:
                    row[1] = 3
                cursor.updateRow(row)

    raw_raster = LineDensity(road, "POPULATION", cell_size=20)
    max_val = raw_raster.maximum
    normalized_raster = raw_raster / max_val
    normalized_raster.save("density_normalized_0_1")

#####################
# Wywołania funkcji #
#####################
#Tą funkcję się uruchamia tylko za pierwszym razem, gdy nie mamy plików shp w geobazie
#import_shp_to_gdb(bdot10k_data, arcpy.env.workspace, acceptable_file_names)

#Funkcja przyjmuje po kolei 3 wartości:
#-odległość bezpieczna od wody
#-odległość która jest dalej akceptowalna ale już mniej
#-maksymalna akceptowalna odległość od wody
#distance_from_water_raster()
#distance_from_buildings_raster()
#distance_from_forest_raster()
road_availability()