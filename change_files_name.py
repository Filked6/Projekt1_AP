import os

def change_name(folder, short, name):
    for file in os.listdir(folder):
        if short in file:
            name_parts = file.split(".")
            extension = name_parts[-1]

            new_name_short = f"{name}.{extension}"

            old_path = os.path.join(folder, file)
            new_path = os.path.join(folder, new_name_short)

            os.rename(old_path, new_path)
            print(f"Zmieniono: {file} -> {new_name_short}")

folder = r"C:\Studia\Sezon_3\Analizy_przestrzenne\Projekt\projekt1\Cwiczenie1_AP\3214_SHP"

change_name(folder, "SWRS", "rzeka")
change_name(folder, "PTWP", "woda")
change_name(folder, "BUBD", "budynek")
change_name(folder, "SKDR", "drogi")
change_name(folder, "PTLZ", "lasy")
change_name(folder, "TCON", "rezerwat1")
change_name(folder, "TCRZ", "rezerwat2")
change_name(folder, "ADJA", "granice")