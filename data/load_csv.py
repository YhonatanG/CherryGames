import csv
from datetime import datetime
from pymongo import MongoClient
import os
import ast

def convertir_k(valor):
    """Convierte strings tipo '3.9K' a enteros como 3900"""
    if isinstance(valor, str) and 'K' in valor:
        try:
            return int(float(valor.replace('K', '')) * 1000)
        except ValueError:
            return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None

def parsear_fecha(fecha_str):
    """Convierte fechas como 'Feb 25, 2022' a datetime"""
    try:
        return datetime.strptime(fecha_str.strip(), "%b %d, %Y")
    except Exception:
        return None

def cargar_csv(csv_file_path):
    # Conexión a MongoDB
    mongo_uri = os.environ.get("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["cherrydb"]
    coleccion = db["videojuegos"]
    coleccion.delete_many({})  # Limpiar antes de insertar

    with open(csv_file_path, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        juegos = []
        for fila in reader:
            try:
                juego = {
                    "title": fila["Title"].strip(),
                    "release_date": parsear_fecha(fila["Release Date"]),
                    "team": ast.literal_eval(fila["Team"]) if fila["Team"].startswith("[") else [fila["Team"]],
                    "rating": float(fila["Rating"]) if fila["Rating"] else None,
                    "times_listed": convertir_k(fila["Times Listed"]),
                    "number_of_reviews": convertir_k(fila["Number of Reviews"]),
                    "genres": ast.literal_eval(fila["Genres"]) if fila["Genres"].startswith("[") else [fila["Genres"]],
                    "summary": fila["Summary"],
                    "reviews": ast.literal_eval(fila["Reviews"]) if fila["Reviews"].startswith("[") else [fila["Reviews"]],
                    "plays": convertir_k(fila["Plays"]),
                    "playing": convertir_k(fila["Playing"]),
                    "backlogs": convertir_k(fila["Backlogs"]),
                    "wishlist": convertir_k(fila["Wishlist"])
                }
                juegos.append(juego)
            except Exception as e:
                print(f"❌ Error procesando fila: {e}")

        if juegos:
            resultado = coleccion.insert_many(juegos)
            print(f"✅ {len(resultado.inserted_ids)} juegos insertados correctamente.")
        else:
            print("⚠️ No se insertó ningún juego.")

if __name__ == "__main__":
    cargar_csv("data/games.csv")
