import csv
from datetime import datetime
from pymongo import MongoClient
import csv
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

def cargar_csv(ruta_csv):
    cliente = MongoClient("mongodb+srv://ygarciab2:Naruto1@cherrygames.hrgsraa.mongodb.net/")
    db = cliente["mi_base_de_datos"]
    coleccion = db["juegos"]

    if coleccion.count_documents({}) == 0:
        with open(ruta_csv, newline='', encoding='utf-8') as archivo_csv:
            lector = csv.DictReader(archivo_csv)
            juegos = list(lector)
            coleccion.insert_many(juegos)
            print(f"✅ {len(juegos)} juegos insertados correctamente.")
    else:
        print("⚠️ Los juegos ya estaban insertados. No se hizo nada.")

if __name__ == "__main__":
    cargar_csv("data/games.csv")
