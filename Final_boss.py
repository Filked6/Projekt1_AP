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
arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("Network")

#################################
# Ścieżki do danych do projektu #
#################################
bdot10k_data = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\3214_SHP"
acceptable_file_names = ("budynek", "drogi", "lasy", "rezerwat1", "rezerwat2", "woda", "rzeka", "granice")
dem_full_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Marianowo_nmt.tif"
xml = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\network_road_xml.xml"
facilities_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\facilities_network.shp"

project_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Projekt1_AP.aprx"
aprx = arcpy.mp.ArcGISProject(project_path)

###########
# Funkcje #
###########
def import_shp_to_gdb(shp_folder, gdb, startings, xml_schema):
    folder = os.listdir(shp_folder)
    feature_dataset = "SiecDrogowa"

    print("(0/2) Importuję pliki .shp z BDOT10k")
    for shp in folder:
        if shp.startswith(startings) and shp.endswith(".shp"):
            full_path = os.path.join(shp_folder, shp)

            out_name = os.path.splitext(shp)[0]
            if out_name == "drogi":
                out_name = "drogi_dla_rastra"
            out_path = os.path.join(gdb, out_name)

            print(f"Importuję do GDB: {shp} -> {out_name}")
            arcpy.management.CopyFeatures(full_path, out_path)

    try:
        print("Budowanie sieci drogowej...")
        arcpy.management.CreateFeatureDataset(gdb, "SiecDrogowa", spatial_reference=arcpy.SpatialReference(2180))
    except:
        print("Sieć drogowa już istnieje.")

    arcpy.conversion.FeatureClassToFeatureClass(f"{shp_folder}\\drogi.shp", f"{gdb}\\{feature_dataset}", "drogi")
    arcpy.na.CreateNetworkDatasetFromTemplate(xml_schema, f"{gdb}\\{feature_dataset}")

    nd_path = f"{gdb}\\{feature_dataset}\\netword_road"
    arcpy.na.BuildNetwork(nd_path)
    print("(1/2) Zbudowano sieć drogową i załadowano pliki shp.")

def import_nmt_to_gdb(dem_path):
    print("(1/2) Dodaję raster do bazy")
    arcpy.management.CopyRaster(dem_path, "nmt")
    print("(2/2) Dodano raster do bazy")

def distance_from_water_raster(min_val = 100, mean_val = 300, max_val = 1000):
    river = "rzeka"
    water = "woda"

    print("Łączę wszystkie pliki z wodą...")
    river_a = arcpy.analysis.Buffer(river, "rzeka_a", "2 Meters")
    water_all = arcpy.management.Merge([river_a, water], "woda_cala")
    distance_raster = DistanceAccumulation(water_all)
    distance_raster.save("distance_raster")

    f = FuzzyLinear(max_val, mean_val)
    temp_fuzzy_raster = FuzzyMembership(distance_raster, f)

    print("1. Tworzenie rastera odległości od wody...")
    distance_raster_final = Con(distance_raster < min_val, 0, temp_fuzzy_raster)
    distance_raster_final.save("distance_raster_water")

    #Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("woda_cala")
    arcpy.management.Delete("rzeka_a")
    arcpy.management.Delete("distance_raster")

def distance_from_buildings_raster(min_from_building = 150, better = 1500 ):
    buildings = "budynek"

    print("Wybieranie budynków mieszkalnych...")
    condition = "\"FOBUD\" = 'budynki mieszkalne'"
    residental = arcpy.analysis.Select(buildings, "mieszkalne", condition)
    distance_raster = DistanceAccumulation(residental)
    distance_raster.save("distance_raster_temp")

    print("2. Tworzenie rastra odległości od budynków mieszkalnych...")
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

    print("Łączenie lasów i obszarów chronionych.")
    land_cover = arcpy.management.Merge([forest, protected1, protected2], "pokrycie_cale")
    distance_raster = DistanceAccumulation(land_cover)
    distance_raster.save("distance_raster_land_cover_temp")

    print("3. Tworzenie rastra odległości od lasów i obszarów chronionych.")
    f = FuzzyLinear(min_from_forest, better)
    fuzzy_raster = FuzzyMembership(distance_raster, f)
    fuzzy_raster.save("distance_raster_land_cover")

    # Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("pokrycie_cale")
    arcpy.management.Delete("distance_raster_land_cover_temp")

def road_availability_raster():
    road = "drogi_dla_rastra"
    column_values1 = ["żwir", "tłuczeń"]
    column_values2 = ["kostka kamienna", "bruk", "kostka prefabrykowana"]

    print("4. Tworzę raster dostępności dróg")
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

    raw_raster = LineDensity(road, "POPULATION", cell_size=20, search_radius=3000)
    raw_raster.save("raw_raster")
    max_val = raw_raster.maximum
    normalized_raster = raw_raster / max_val
    normalized_raster.save("density_normalized_0_1")

    arcpy.management.Delete("raw_raster")

def calculate_slope_raster():
    dem = "nmt"
    mask = 10.0

    dem_clean = SetNull(Raster(dem) < 0.1, dem)
    dem_clean.save("dem_cleaned")
    slope_raster = Slope(dem_clean, "DEGREE", 1)
    slope_raster.save("slope_raster_temp")

    print("5. Tworzę raster nachylenia")
    raster_mask = Con(Raster(slope_raster) > mask,0, (mask - Raster(slope_raster)) / mask)
    raster_mask.save("slope_raster")

    arcpy.management.Delete("slope_raster_temp")
    arcpy.management.Delete("dem_cleaned")

def solar_exposure_raster():
    dem = "nmt"
    target_direction = 180 #Południe
    max_diff = 45

    dem_raster = Raster(dem)
    dem_clean = SetNull(dem_raster < 0.1, dem_raster)
    aspect_raster = Aspect(dem_clean)
    aspect_raster.save("solar_exposure_raster_temp")

    diff = Abs(aspect_raster - target_direction)

    print("6. Tworzę raster dostępności do światła")
    aspect_score = Con(diff <= max_diff, 1 - (diff / max_diff),0)
    aspect_score.save("solar_exposure_raster")

    arcpy.management.Delete("solar_exposure_raster_temp")

def calculate_drive_time_raster(shp_file, gdb):
    network_source = f"{gdb}\\SiecDrogowa\\netword_road"

    arcpy.conversion.FeatureClassToFeatureClass(shp_file, gdb, "facilities")
    facilities_path = f"{gdb}\\facilities"

    print("Obliczam odległości od węzłów.")
    solver = arcpy.nax.ServiceArea(network_source)

    solver.distanceUnits = arcpy.nax.DistanceUnits.Meters
    solver.defaultImpedanceCutoffs = [500, 1500, 3000, 5000, 8000, 10000]

    solver.outputType = arcpy.nax.ServiceAreaOutputType.Polygons
    solver.travelDirection = arcpy.nax.TravelDirection.FromFacility
    solver.polygonDetail = arcpy.nax.ServiceAreaPolygonDetail.Standard
    solver.geometryAtOverlap = arcpy.nax.ServiceAreaOverlapGeometry.Dissolve

    solver.geometryAtCutoff = arcpy.nax.ServiceAreaPolygonCutoffGeometry.Rings
    solver.load(arcpy.nax.ServiceAreaInputDataType.Facilities, facilities_path)
    result = solver.solve()

    if result.solveSucceeded:
        output_path = f"{gdb}\\road_map_network"
        result.export(arcpy.nax.ServiceAreaOutputDataType.Polygons, output_path)

    road_network_shp = "road_map_network"

    arcpy.management.AddField(road_network_shp, "SCORE", "FLOAT")
    code_block = """def calc_score(to_break):
        if to_break <= 1500:
            return 1.0
        elif to_break <= 3000:
            return 0.8
        elif to_break <= 5000:
            return 0.6
        elif to_break <= 8000:
            return 0.4
        elif to_break <= 10000:
            return 0.2
        else:
            return 0.0"""

    print("7. Tworzę raster odległości od węzłów.")
    arcpy.management.CalculateField(road_network_shp, "SCORE", "calc_score(!ToBreak!)", "PYTHON3", code_block)
    arcpy.conversion.PolygonToRaster(
        in_features="road_map_network",
        value_field="SCORE",
        out_rasterdataset="road_network_raster",
        cell_assignment="MAXIMUM_AREA",
        priority_field="SCORE",
        cellsize= 10
    )

def combine_rasters():
    lista_rastrow = [
        "distance_raster_water",
        "distance_raster_residental",
        "distance_raster_land_cover",
        "density_normalized_0_1",
        "slope_raster",
        "solar_exposure_raster",
        "road_network_raster"
    ]
    boarders = "granice"

    print("Łączę rastry...")

    raster_min = CellStatistics(lista_rastrow, "MINIMUM", "DATA")
    raster_mean = CellStatistics(lista_rastrow, "MEAN", "DATA")

    raster = Con(raster_min == 0, 0, raster_mean)
    raster.save("raster_merged")
    print("Raster został poprawnie połączony...")
    print("Przycinanie rastra do wybranej gminy...")

    arcpy.management.MakeFeatureLayer(boarders, "granice_temp")
    arcpy.management.SelectLayerByAttribute("granice_temp", "NEW_SELECTION", "NAZWA = 'Marianowo'")
    raster_clipped = ExtractByMask(raster, "granice_temp")
    raster_clipped.save(f"przyciety_raster")

    arcpy.management.Delete("granice_temp")

#####################
# Wywołania funkcji #
#####################
#Tą funkcję się uruchamia tylko za pierwszym razem, gdy nie mamy plików shp w geobazie
import_shp_to_gdb(bdot10k_data, arcpy.env.workspace, acceptable_file_names, xml)
import_nmt_to_gdb(dem_full_path)

distance_from_water_raster()
distance_from_buildings_raster()
distance_from_forest_raster()
road_availability_raster()
calculate_slope_raster()
solar_exposure_raster()
calculate_drive_time_raster(facilities_path, arcpy.env.workspace)
combine_rasters()