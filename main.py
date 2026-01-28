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

acceptable_file_names = ("budynek", "drogi", "lasy", "rezerwat1", "rezerwat2", "woda", "rzeka", "granice", "linie_napowietrzne",
                         "PTZB", "PTRK", "PTUT", "PTTR", "PTKM", "PTGN", "PTPL", "PTSO", "PTWZ", "PTNZ")
#################################
# Ścieżki do danych do projektu #
#################################


bdot10k_data = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\3214_SHP"
dem_full_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Marianowo_nmt.tif"
xml = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\network_road_xml.xml"
facilities_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\facilities_network.shp"
parcels_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\marianowo_dzialki.shp"

project_path = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Projekt1_AP_POPRAWNY\Projekt1_AP\Projekt1_AP.aprx"
aprx = arcpy.mp.ArcGISProject(project_path)


###########
# Funkcje #
###########
def import_shp_to_gdb(shp_folder, gdb, startings, xml_schema):
    folder = os.listdir(shp_folder)
    feature_dataset = "SiecDrogowa"

    print("(0/2) Importuję pliki .shp z BDOT10k")
    arcpy.management.CopyFeatures(parcels_path, "dzialki")

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

    print("Kryterium 1: Odległość od rzek i zbiorników wodnych")
    print("Łączenie wód...")
    river_a = arcpy.analysis.Buffer(river, "rzeka_a", "2 Meters")
    water_all = arcpy.management.Merge([river_a, water], "woda_cala")
    distance_raster = DistanceAccumulation(water_all)
    distance_raster.save("distance_raster")

    f = FuzzyLinear(max_val, mean_val)
    temp_fuzzy_raster = FuzzyMembership(distance_raster, f)

    temp_raster_with_zeros = Con(distance_raster < min_val, 0, temp_fuzzy_raster)

    print("Tworzenie rastra z odległością od wód...")
    distance_raster_final = SetNull(distance_raster > (max_val - 50), temp_raster_with_zeros)
    distance_raster_final.save("distance_raster_water")

    #Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("woda_cala")
    arcpy.management.Delete("rzeka_a")
    arcpy.management.Delete("distance_raster")

def distance_from_buildings_raster(min_from_building = 150, better = 1500 ):
    buildings = "budynek"

    print("Kryterium 2: Odległość od budynków mieszkalnych.")
    print("Wybieranie budynków mieszkalnych...")
    condition = "\"FOBUD\" = 'budynki mieszkalne'"
    residental = arcpy.analysis.Select(buildings, "mieszkalne", condition)
    distance_raster = DistanceAccumulation(residental)
    distance_raster.save("distance_raster_temp")

    print("Tworzenie rastra odległości od budynków mieszkalnych...")
    f = FuzzyLinear(min_from_building, better)
    fuzzy_raster = FuzzyMembership(distance_raster, f)
    fuzzy_raster.save("distance_raster_residental")

    #Czyszczenie
    arcpy.management.Delete("mieszkalne")
    arcpy.management.Delete("distance_raster_temp")

def distance_from_forest_raster(min_from_forest = 15, better = 100):
    forest = "lasy"
    protected1 = "rezerwat1"
    protected2 = "rezerwat2"

    print("Kryterium 3: Pokrycie terenu.")
    print("Łączenie lasów i obszarów chronionych...")
    land_cover = arcpy.management.Merge([forest, protected1, protected2], "pokrycie_cale")
    distance_raster = DistanceAccumulation(land_cover)
    distance_raster.save("distance_raster_land_cover_temp")

    print("Tworzenie rastra odległości od lasów i obszarów chronionych...")
    f = FuzzyLinear(min_from_forest, better)
    fuzzy_raster = FuzzyMembership(distance_raster, f)
    fuzzy_raster.save("distance_raster_land_cover")

    # Usuwanie tego co jest po drodze, jeśli potrzebne to trza zakomentować i będzie git
    arcpy.management.Delete("pokrycie_cale")
    arcpy.management.Delete("distance_raster_land_cover_temp")

def road_availability_raster():
    road = "drogi_dla_rastra"

    print("Kryterium 4: Dostęp do dróg utwardzonych")
    print("Tworzę raster dostępności dróg")
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
                else:
                    row[1] = 2
                cursor.updateRow(row)

    raw_raster = LineDensity(road, "POPULATION", cell_size=20, search_radius=3000)
    raw_raster.save("raw_raster")
    max_val = raw_raster.maximum
    normalized_raster = raw_raster / max_val
    normalized_raster.save("density_normalized_0_1")

    #Usuwanie niepotrzebnych pozostałości
    arcpy.management.Delete("raw_raster")

def calculate_slope_raster(mask = 10.0):
    dem = "nmt"

    print("Kryterium 5: Nachylenie stoków.")
    dem_clean = SetNull(Raster(dem) < 0.1, dem)
    dem_clean.save("dem_cleaned")
    slope_raster = Slope(dem_clean, "DEGREE", 1)
    slope_raster.save("slope_raster_temp")

    print("Tworzę raster nachylenia")
    raster_mask = Con(Raster(slope_raster) > mask,0, (mask - Raster(slope_raster)) / mask)
    raster_mask.save("slope_raster")

    #Usuwanie niepotrzebnych pozostałości
    arcpy.management.Delete("slope_raster_temp")
    arcpy.management.Delete("dem_cleaned")

def solar_exposure_raster():
    dem = "nmt"
    target_direction = 180 #Południe
    max_diff = 45

    print("Kryterium 6: Dostęp do światła słonecznego")
    dem_raster = Raster(dem)
    dem_clean = SetNull(dem_raster < 0.1, dem_raster)
    aspect_raster = Aspect(dem_clean)
    aspect_raster.save("solar_exposure_raster_temp")

    diff = Abs(aspect_raster - target_direction)

    print("Tworzę raster dostępności do światła...")
    aspect_score = Con(diff <= max_diff, 1 - (diff / max_diff),0)
    aspect_score.save("solar_exposure_raster")

    # Usuwanie niepotrzebnych pozostałości
    arcpy.management.Delete("solar_exposure_raster_temp")

def calculate_drive_time_raster(shp_file, gdb):
    network_source = f"{gdb}\\SiecDrogowa\\netword_road"

    print("Kryterium 7: Dobry dojazd od istotnych drogowych węzłów komunikacyjnych.")
    arcpy.conversion.FeatureClassToFeatureClass(shp_file, gdb, "facilities")
    facilities_path = f"{gdb}\\facilities"

    print("Obliczam odległości od węzłów.")
    solver = arcpy.nax.ServiceArea(network_source)

    solver.distanceUnits = arcpy.nax.DistanceUnits.Meters
    solver.defaultImpedanceCutoffs = [500, 1000, 1500, 2500, 3500, 5000, 6500, 8500, 10500]

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

    arcpy.management.AddField("road_map_network", "SCORE", "FLOAT")
    code_block = """def calc_score(to_break):
        if to_break <= 500:
            return 1.0
        elif to_break <= 1000:
            return 0.95
        elif to_break <= 1500:
            return 0.90
        elif to_break <= 2500:
            return 0.80        
        elif to_break <= 3500:
            return 0.70
        elif to_break <= 5000:
            return 0.60
        elif to_break <= 6500:
            return 0.40
        elif to_break <= 8500:
            return 0.20
        elif to_break <= 12500:
            return 0.0"""

    print("Tworzę raster odległości od węzłów.")
    arcpy.management.CalculateField("road_map_network", "SCORE",
                                    "calc_score(!ToBreak!)", "PYTHON3", code_block)
    arcpy.conversion.PolygonToRaster(
        in_features="road_map_network",
        value_field="SCORE",
        out_rasterdataset="road_network_raster",
        cell_assignment="MAXIMUM_AREA",
        priority_field="SCORE",
        cellsize= arcpy.env.cellSize
    )

def combine_rasters(gmina = "Marianowo"):
    weights = {
        "distance_raster_water": 0.10,
        "distance_raster_residental": 0.10,
        "distance_raster_land_cover": 0.15,
        "density_normalized_0_1": 0.05,
        "slope_raster": 0.20,
        "solar_exposure_raster": 0.20,
        "road_network_raster": 0.20
    }
    boarders = "granice"

    print("Łączę rastry...")

    lista_rastrow = list(weights.keys())
    raster_min = CellStatistics(lista_rastrow, "MINIMUM", "DATA")

    raster_weighted_sum = 0
    for raster_name, weight in weights.items():
        raster_weighted_sum += Raster(raster_name) * weight

    raster = Con(raster_min == 0, 0, raster_weighted_sum)
    raster.save("raster_merged")

    print("Rastry zostały połączone.")
    print("Przycinanie rastra do wybranej gminy...")

    arcpy.management.MakeFeatureLayer(boarders, "granice_temp")
    arcpy.management.SelectLayerByAttribute("granice_temp", "NEW_SELECTION", f"NAZWA = '{gmina}'")
    raster_clipped = ExtractByMask(raster, "granice_temp")
    raster_clipped.save("przyciety_raster")

    in_raster = Raster("przyciety_raster")
    min_result = arcpy.GetRasterProperties_management(in_raster, "MINIMUM").getOutput(0)
    max_result = arcpy.GetRasterProperties_management(in_raster, "MAXIMUM").getOutput(0)

    min_val = float(min_result.replace(',', '.'))
    max_val = float(max_result.replace(',', '.'))

    if max_val != min_val:
        normalized_raster = (in_raster - min_val) / (max_val - min_val)
        normalized_raster.save("normalized_raster")
    else:
        in_raster.save("normalized_raster")

    arcpy.management.Delete("granice_temp")
    arcpy.management.Delete("przyciety_raster")

def choose_appropriate_parcel(min_cover_pct = 50, min_area_ha = 2, min_width = 50, usefulness = 0.70):
    parcels = "dzialki"
    normalized_raster = Raster("normalized_raster")
    id_field = "OBJECTID"
    min_area = min_area_ha * 10000

    print("Kryterium 8: Ocena przydatności terenu. Min. 70% przydatności terenu.")
    print("Wycinanie miejsc z mniejszą przydatnością...")
    reclass_raster = Con((normalized_raster >= usefulness) & (normalized_raster <= 1), 1)
    temp_polygons = arcpy.RasterToPolygon_conversion(reclass_raster, "memory/temp1", "NO_SIMPLIFY", "VALUE")

    arcpy.sa.TabulateArea(parcels, id_field, reclass_raster, "Value", "memory/area_table")

    arcpy.management.JoinField(parcels, id_field, "memory/area_table", id_field, ["VALUE_1"])

    print("Kryterium 9: Przydatny obszar. Min. 50% na terenie działki")
    where_clause = f"VALUE_1 IS NOT NULL AND (VALUE_1 / Shape_Area) * 100 >= {min_cover_pct} AND KLASOUZYTK <> 'dr'"
    suitable_parcels = arcpy.analysis.Select(parcels, "memory/suitable_parcels_temp", where_clause)

    arcpy.management.Dissolve(in_features=suitable_parcels, out_feature_class="suitable_parcels_merged", dissolve_field=None,
        statistics_fields=None, multi_part="SINGLE_PART", unsplit_lines="DISSOLVE_LINES")

    final_clipped_areas = arcpy.analysis.Clip(in_features= temp_polygons, clip_features="suitable_parcels_merged", out_feature_class="obszary_na_dzialkach")

    small_polys = arcpy.management.MultipartToSinglepart(in_features=final_clipped_areas, out_feature_class="obszary_pojedyncze")

    arcpy.management.AddField("suitable_parcels_merged", "Zestaw", "LONG")
    with arcpy.da.UpdateCursor("suitable_parcels_merged", ["Zestaw"]) as cursor:
        i = 1
        for row in cursor:
            row[0] = i
            cursor.updateRow(row)
            i += 1

    arcpy.analysis.SpatialJoin(target_features=small_polys, join_features="suitable_parcels_merged", out_feature_class="tagged_polygons",
        join_operation="JOIN_ONE_TO_ONE", match_option="HAVE_THEIR_CENTER_IN")

    final_multipolygons = arcpy.management.Dissolve(in_features="tagged_polygons", out_feature_class="zestawy_finalne_multipolygon", dissolve_field=["Zestaw"],
        statistics_fields=None, multi_part="MULTI_PART", unsplit_lines="DISSOLVE_LINES")

    print("Kryterium 10: Powierzchnia obszaru powyżej 2ha.")
    wc1 = f'Shape_Area >= {min_area}'
    arcpy.analysis.Select(final_multipolygons, "pole", wc1)

    print("Kryterium 11: Szerokość obszaru w pionie lub poziomie min. 50 metrów.")
    arcpy.management.AddField("pole", "width", "FLOAT")
    arcpy.management.AddField("pole", "height", "FLOAT")

    with arcpy.da.UpdateCursor("pole", ["SHAPE@", "width", "height"]) as cursor:
        for row in cursor:
            geom = row[0]
            ext = geom.extent

            row[1] = abs(ext.XMin - ext.XMax)
            row[2] = abs(ext.YMin - ext.YMax)

            cursor.updateRow(row)

    wc2 = f'width >= {min_width} OR height >= {min_width}'
    arcpy.analysis.Select("pole", "final_to_parcel", wc2)

    arcpy.management.MakeFeatureLayer("suitable_parcels_merged", "duze_layer")
    arcpy.management.SelectLayerByLocation(in_layer="duze_layer", select_features="final_to_parcel", selection_type="NEW_SELECTION")
    arcpy.management.CopyFeatures("duze_layer", "kandydaci")

    #Czyszczenie
    arcpy.management.Delete("suitable_parcels_merged")
    arcpy.management.Delete("obszary_pojedyncze")
    arcpy.management.Delete("tagged_polygons")
    #arcpy.management.Delete("zestawy_finalne_multipolygon")
    arcpy.management.Delete("pole")
    arcpy.management.Delete("final_to_parcel")
    arcpy.management.Delete("duze_layer")


def map_cost(bdot, gdb):
    parcels = "kandydaci"
    airlines = "linie_napowietrzne"
    borders = "granice"

    print("Kryterium 12: Koszt przyłącza do sieci SN.")
    wc = "RODZAJ <> 'linia telekomunikacyjna'"

    electrolines = arcpy.analysis.Select(airlines, "linie_energetyczne", where_clause=wc)

    arcpy.management.MakeFeatureLayer(parcels, "kandydaci_layer_check")
    arcpy.management.SelectLayerByLocation(
        in_layer="kandydaci_layer_check",
        overlap_type="INTERSECT",
        select_features="linie_energetyczne",
        selection_type="NEW_SELECTION"
    )

    direct_count = int(arcpy.management.GetCount("kandydaci_layer_check").getOutput(0))

    if direct_count > 0:
        print(f"Znaleziono {direct_count} działek przecinających linię energetyczną..")
        arcpy.management.CopyFeatures("kandydaci_layer_check", "Winner")
        arcpy.management.Delete("kandydaci_layer_check")

    arcpy.management.Delete("kandydaci_layer_check")

    count_lines = int(arcpy.management.GetCount("linie_energetyczne").getOutput(0))
    if count_lines == 0:
        print("Brak linii energetycznych.")

    data_mapping = {
        "woda": {"field": "RODZAJ", "values": {"woda morska": 900, "woda płynąca": 200, "woda stojąca": 900}},
        "PTZB": {"field": "RODZAJ",
        "values": {"jednorodzinna": 100, "wielorodzinna": 200, "inna": 50, "handlowo_usługowa": 200,
        "przemysłowo-składowa": 200}},
        "lasy": {"field": "RODZAJ", "values": {"las": 100, "zagajnik": 50, "zadrzewienie": 50}},
        "PTRK": {"field": "RODZAJ", "values": {"krzewy": 15}},
        "PTUT": {"field": "RODZAJ", "values": {"sad": 100, "plantacja": 90, "inne": 20, "ogródkki działkowe": 900}},
        "PTTR": {"field": "RODZAJ", "values": {"uprawa na gruntach ornych": 1, "roślinność trawiasta": 20}},
        "PTKM": {"field": "KOD10K", "values": 200},
        "PTGN": {"field": "KOD10K", "values": 1},
        "PTPL": {"field": "KOD10K", "values": 50},
        "PTSO": {"field": "KOD10K", "values": 900},
        "PTWZ": {"field": "KOD10K", "values": 900},
        "PTNZ": {"field": "KOD10K", "values": 150}
    }

    list_of_rasters = []
    if arcpy.Exists(borders):
        try:
            arcpy.management.AddField(borders, "BASE_COST", "SHORT")
            arcpy.management.CalculateField(borders, "BASE_COST", "1", "PYTHON3")
        except:
            pass

    out_bg_raster = os.path.join(gdb, "r_background")
    arcpy.conversion.FeatureToRaster(borders, "BASE_COST", out_bg_raster, arcpy.env.cellSize)
    list_of_rasters.append(out_bg_raster)

    for name, info in data_mapping.items():
        shp_path = os.path.join(bdot, f"{name}.shp")
        if arcpy.Exists(shp_path):
            print(f"Przetwarzam: {name}")
            raster_name = f"r_{name}".replace(".", "_")
            out_raster_path = os.path.join(gdb, raster_name)
            temp_field = "COST_VAL"
            if temp_field in [f.name for f in arcpy.ListFields(shp_path)]:
                arcpy.management.DeleteField(shp_path, temp_field)
            arcpy.management.AddField(shp_path, temp_field, "FLOAT")
            mapping_values = info["values"]
            field_name = info["field"]
            with arcpy.da.UpdateCursor(shp_path, [field_name, temp_field]) as cursor:
                for row in cursor:
                    if isinstance(mapping_values, dict):
                        val = mapping_values.get(row[0], 0)
                        if val is None: val = 0
                    else:
                        val = mapping_values
                        if val is None: val = 0
                    row[1] = val
                    cursor.updateRow(row)
            temp_raw_rast = os.path.join("memory", "temp_raw")
            arcpy.conversion.FeatureToRaster(shp_path, temp_field, temp_raw_rast, arcpy.env.cellSize)
            cleaned_raster = SetNull(temp_raw_rast, temp_raw_rast, "VALUE = 0")
            cleaned_raster.save(out_raster_path)
            list_of_rasters.append(out_raster_path)
            arcpy.management.Delete(temp_raw_rast)
    print("Łączenie rastrów...")
    arcpy.management.MosaicToNewRaster(input_rasters=list_of_rasters, output_location=gdb,
    raster_dataset_name_with_extension="final_raster_for_cost_distance",
    pixel_type="32_BIT_FLOAT", cellsize=arcpy.env.cellSize, number_of_bands=1,
    mosaic_method="MAXIMUM")
    for r in list_of_rasters:
        if "r_background" not in r:
            arcpy.management.Delete(r)
    print("Tworzenie mapy kosztów i wyznaczanie trasy...")
    out_distance_raster = CostDistance(parcels, Raster("final_raster_for_cost_distance"),
    out_backlink_raster="kierunki")
    arcpy.management.CalculateStatistics("kierunki")
    out_path_raster = CostPath(in_destination_data=electrolines, in_cost_distance_raster=out_distance_raster,
    in_cost_backlink_raster="kierunki", path_type="BEST_SINGLE")
    out_path_raster.save("Ostateczna_linia")

    try:
        arcpy.conversion.RasterToPolyline(out_path_raster, "path_polyline", "NODATA", 0, "SIMPLIFY")

        line_count = int(arcpy.management.GetCount("path_polyline").getOutput(0))
        if line_count > 0:
            arcpy.management.MakeFeatureLayer(parcels, "parcels_layer")
            arcpy.management.SelectLayerByLocation(in_layer="parcels_layer", overlap_type="INTERSECT",
            select_features="path_polyline", selection_type="NEW_SELECTION")
            arcpy.management.CopyFeatures("parcels_layer", "Winner")
            print("Wybrano zwycięzcę.")
    except Exception as e:
        print(f"Błąd podczas tworzenia linii: {e}")

    if arcpy.Exists("path_polyline"): arcpy.management.Delete("path_polyline")

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
choose_appropriate_parcel()
map_cost(bdot10k_data, arcpy.env.workspace)