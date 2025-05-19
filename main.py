from flask import Flask, render_template, request, redirect, url_for
from flask import session, flash
from functools import wraps
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from datetime import datetime
from urllib.parse import urlencode
from data.load_csv import cargar_csv

app = Flask(__name__, template_folder="web/templates")
app.secret_key = "987654321"  
client = MongoClient(os.environ["MONGO_URI"])
db = client["cherrydb"]
coleccion = db["videojuegos"]
coleccion_usuarios = db["usuarios"]

# Cargar CSV solo si la colección está vacía
if db["videojuegos"].count_documents({}) == 0:
    ruta_csv = 'data/games.csv'
    cargar_csv(ruta_csv)
    print("✅ Datos cargados desde CSV")
else:
    print("📦 Datos ya existen en la base de datos")

#El usuario Admin
if not coleccion_usuarios.find_one({"usuario": "admin"}):
    coleccion_usuarios.insert_one({
        "usuario": "admin",
        "clave": "1234"
    })
    print("Usuario 'admin' creado.")
else:
    print("El usuario 'admin' ya existe.")
    
def parsear_fecha(fecha_str):
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d")
    except:
        return None


def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if "usuario" not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorada

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]
        user = coleccion_usuarios.find_one({"usuario": usuario, "clave": clave})
        if user:
            session["usuario"] = usuario
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("index"))
        else:
            flash("Credenciales incorrectas", "danger")
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))

@app.route("/usuarios", methods=["GET", "POST"])
@login_requerido
def gestionar_usuarios():
    if session["usuario"] != "admin":
        flash("Solo el administrador puede acceder a esta sección.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        if "nuevo_usuario" in request.form:
            # Crear nuevo usuario
            nuevo_usuario = request.form["nuevo_usuario"]
            clave = request.form["clave"]
            if coleccion_usuarios.find_one({"usuario": nuevo_usuario}):
                flash("El usuario ya existe", "warning")
            else:
                coleccion_usuarios.insert_one({
                    "usuario": nuevo_usuario,
                    "clave": clave
                })
                flash("Usuario agregado correctamente", "success")
        elif "borrar_usuario" in request.form:
            usuario_a_borrar = request.form["borrar_usuario"]
            if usuario_a_borrar == "admin":
                flash("No puedes eliminar al usuario administrador principal.", "danger")
            elif usuario_a_borrar == session["usuario"]:
                flash("No puedes eliminarte a ti mismo.", "warning")
            else:
                coleccion_usuarios.delete_one({"usuario": usuario_a_borrar})
                flash(f"Usuario '{usuario_a_borrar}' eliminado", "info")

        return redirect(url_for("gestionar_usuarios"))

    usuarios = list(coleccion_usuarios.find())
    return render_template("usuarios.html", usuarios=usuarios)



@app.route("/")
def index():
    # --- filtros y paginación (igual que antes) ---
    q       = request.args.get("q", "").strip()
    genre   = request.args.get("genre", "").strip()
    year    = request.args.get("year", "").strip()
    rating  = request.args.get("rating", "").strip()
    page    = int(request.args.get("page", 1))
    per_page= 20

    filtro = {}
    if q:      filtro["title"] = {"$regex": q, "$options": "i"}
    if genre:  filtro["genres"] = genre
    if year:
        try:
            y = int(year)
            filtro["release_date"] = {
                "$gte": datetime(y,1,1),
                "$lt":  datetime(y+1,1,1)
            }
        except: pass
    if rating:
        try:
            filtro["rating"] = {"$gte": float(rating)}
        except: pass

    total = coleccion.count_documents(filtro)
    juegos = list(coleccion
                  .find(filtro)
                  .skip((page-1)*per_page)
                  .limit(per_page))

    # géneros únicos
    generos = [g["_id"] for g in coleccion.aggregate([
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres"}},
        {"$sort": {"_id": 1}}
    ])]

    has_more = total > page*per_page
    # preparar query string sin page
    query_args = request.args.to_dict()
    query_args.pop("page", None)
    qs = urlencode(query_args)

    return render_template("index.html",
        juegos=juegos,
        generos=generos,
        genre=genre,
        page=page,
        has_more=has_more,
        query_string=qs
    )
@app.route("/juego/<game_id>")
def detalle_juego(game_id):
    juego = coleccion.find_one({"_id": ObjectId(game_id)})
    if not juego:
        return "Juego no encontrado", 404
    return render_template("detalle.html", juego=juego)

@app.route("/add", methods=["GET", "POST"])
@login_requerido
def add():
    
    # Obtener la lista de géneros existentes
    generos = [g["_id"] for g in coleccion.aggregate([
        {"$unwind": "$genres"},
        {"$group": {"_id": "$genres"}},
        {"$sort": {"_id": 1}}
    ])]

    if request.method == "POST":
        new = {
            "title": request.form["title"],
            "release_date": parsear_fecha(request.form["release_date"]),
            "team": [t.strip() for t in request.form["team"].split(",") if t.strip()],
            "rating": float(request.form["rating"] or 0),
            # Tomamos la lista enviada por el select múltiple
            "genres": request.form.getlist("genres"),
            "summary": request.form["summary"]
        }
        coleccion.insert_one(new)
        return redirect(url_for("index"))

    # En GET pasamos 'generos' al template
    return render_template("add.html", generos=generos)

    
@app.route("/edit/<game_id>", methods=["GET", "POST"])
@login_requerido
def edit(game_id):
    juego = coleccion.find_one({"_id": ObjectId(game_id)})
    if request.method == "POST":
        update = {
            "title": request.form["title"],
            "release_date": parsear_fecha(request.form["release_date"]),
            "team": [t.strip() for t in request.form["team"].split(",") if t.strip()],
            "rating": float(request.form["rating"] or 0),
            "genres": [g.strip() for g in request.form["genres"].split(",") if g.strip()],
            "summary": request.form["summary"]
        }
        coleccion.update_one(
            {"_id": ObjectId(game_id)},
            {"$set": update}
        )
        return redirect(url_for("index"))
    # pasar datos prellenados
    return render_template("edit.html", juego=juego)

@app.route("/delete/<game_id>", methods=["POST"])
@login_requerido
def delete(game_id):
    coleccion.delete_one({"_id": ObjectId(game_id)})
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
