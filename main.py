from flask import Flask
from data.load_csv import cargar_csv
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ El servidor está funcionando correctamente."

if __name__ == '__main__':
    # Ruta al CSV
    ruta_csv = 'data/games.csv'

    # Cargar datos del CSV si la colección está vacía
    cargar_csv(ruta_csv)

    # Puerto requerido por Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
