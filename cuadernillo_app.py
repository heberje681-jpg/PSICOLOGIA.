import io
import re
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cuadernillo de exploración educativa", page_icon="📋", layout="centered")

# Umbrales HEURÍSTICOS (no validados; el cuadernillo no define puntos de corte).
# Ajústalos con criterio profesional. Se necesita convergencia de varios indicios.
U = {"omisiones": 8, "falsos_pos": 3, "recuerdo": 2, "instrucciones": 3,
     "comprension": 2, "mates": 4, "org_items": 4}

PALABRAS = ["luna", "zapato", "jardín", "moneda", "ventana"]
ACCIONES = ["Nombre arriba", "Círculo abajo a la derecha", "Número 8 dentro del círculo",
            "Nombre subrayado", "ESCUELA debajo del círculo"]
TEXTO = ("**EL PROYECTO ESCOLAR.** Un grupo de estudiantes decidió crear un pequeño huerto en la escuela. "
         "Antes de comenzar, investigaron qué plantas podían crecer en su región y cuánta agua necesitaban. "
         "Después organizaron equipos: unos prepararon la tierra, otros sembraron las semillas y otros "
         "registraron el crecimiento de las plantas. Durante las primeras semanas, algunas semillas no "
         "germinaron porque recibieron demasiada agua. El grupo revisó sus registros, modificó el riego y "
         "finalmente consiguió que la mayoría de las plantas creciera. La experiencia les enseñó que observar "
         "los resultados y corregir los errores es parte del aprendizaje.")
COMP = [("¿Qué decidieron hacer los estudiantes?", "crear un huerto escolar"),
        ("¿Por qué algunas semillas no germinaron?", "recibieron demasiada agua"),
        ("¿Qué hicieron para mejorar los resultados?", "revisaron registros y modificaron el riego"),
        ("¿Qué enseñanza obtuvieron de la experiencia?", "observar resultados y corregir errores es parte del aprendizaje")]
MATES = [("Completa la secuencia: 3, 6, 9, 12, ___", ["15"], "15"),
         ("¿Cuál es el resultado de 48 ÷ 6?", ["8"], "8"),
         ("Si un cuaderno cuesta $18, ¿cuánto cuestan 3 cuadernos?", ["54"], "$54"),
         ("¿Qué número falta? 5, 10, 20, 40, ___", ["80"], "80"),
         ("Un estudiante leyó 24 páginas el lunes y 17 el martes. ¿Cuántas leyó en total?", ["41"], "41"),
         ("Una actividad empieza a las 10:15 y dura 35 minutos. ¿A qué hora termina?", ["10.50"], "10:50"),
         ("Escribe los números en orden de menor a mayor: 0.8, 0.25, 1.2", ["0.25", "0.8", "1.2"], "0.25, 0.8, 1.2"),
         ("Si 4 paquetes contienen 6 lápices cada uno, ¿cuántos lápices hay en total?", ["24"], "24")]
ORG = ["Olvido qué materiales debo llevar a clase.",
       "Comienzo una tarea, pero me cuesta terminarla.",
       "Necesito que me recuerden varias veces qué debo hacer.",
       "Me cuesta organizar una actividad con varios pasos.",
       "Entrego trabajos incompletos por no revisar las instrucciones.",
       "Me cuesta calcular cuánto tiempo necesito para una tarea.",
       "Respondo o actúo antes de pensar qué puede ocurrir.",
       "Me cuesta volver a una actividad después de una interrupción."]
NIV = {0: "Nunca o casi nunca", 1: "Algunas veces", 2: "Frecuentemente", 3: "Casi siempre"}
APOYOS = ["Instrucciones en pasos cortos", "Repetir o reformular instrucciones", "Apoyo visual / agenda",
          "Tiempo adicional", "Revisión conjunta de tareas", "Lectura guiada o preguntas orales",
          "Práctica adicional en matemáticas", "Asiento cercano al docente / menos distractores",
          "Entrevista con familia", "Revisión de visión / audición"]
AREAS = {
    "Atención y funciones ejecutivas (explorar TDAH u otras causas)": (
        "Entrevista con familia y docentes, escalas validadas con varios informantes y observación en más de un "
        "contexto. Para considerar TDAH, los síntomas deben iniciar antes de los 12 años y verse en al menos dos ambientes.",
        "sueño, ansiedad o ánimo, visión/audición, ausencias, estrés familiar, método de estudio"),
    "Memoria verbal inmediata y seguimiento de instrucciones": (
        "Prueba estandarizada de memoria de trabajo/verbal y revisión de la audición.",
        "audición, interrupciones al leer las palabras, ansiedad, idioma"),
    "Lectura, comprensión y escritura (explorar dificultad específica del aprendizaje)": (
        "Valoración psicopedagógica con pruebas estandarizadas e historia escolar. La dificultad debe persistir "
        "pese a apoyos y práctica adecuados.",
        "visión/audición, rezago escolar o ausencias, idioma, falta de práctica, ansiedad"),
    "Razonamiento y cálculo matemático (explorar dificultad específica en matemáticas)": (
        "Valoración psicopedagógica de cálculo y razonamiento, revisando el procedimiento y no solo el resultado.",
        "ansiedad ante matemáticas, rezago escolar, instrucción previa, errores por falta de atención"),
}

S = st.session_state
store = S.setdefault("_store", {})  # conserva datos del aplicador al cambiar de modo
for k, v in store.items():
    S.setdefault(k, v)
S.setdefault("_modo", "apl")
S.setdefault("w_pin", "1234")


def acierta(texto, esperado):
    toks = re.findall(r"\d+(?:[.:]\d+)?", (texto or "").replace(":", "."))
    return toks == esperado


# ================= MODO ESTUDIANTE =================
if S["_modo"] == "est":
    st.title("Actividades para el estudiante")
    if S.get("_entregado"):
        st.success("¡Gracias por participar! Devuelve el dispositivo a tu aplicador(a).")
        pin = st.text_input("PIN del aplicador(a)", type="password", key="_pin_in")
        if st.button("Volver"):
            if pin == S["w_pin"]:
                S["_modo"] = "apl"
                st.rerun()
            st.error("PIN incorrecto.")
        st.stop()
    st.caption("No es un examen para calificarte. Si no sabes una respuesta, déjala en blanco y continúa.")
    st.header("Actividad 3. Comprensión lectora")
    st.info(TEXTO)
    for i, (q, _) in enumerate(COMP):
        st.text_area(f"{i + 1}. {q}", key=f"s_c{i}")
    st.header("Actividad 5. Razonamiento y matemáticas")
    st.caption("Sin calculadora.")
    for i, (q, _, _) in enumerate(MATES):
        st.text_input(f"{i + 1}. {q}", key=f"s_m{i}")
    st.header("Actividad 6. Cómo organizo mis tareas")
    st.caption("Piensa en lo que te sucede normalmente durante las últimas cuatro semanas.")
    for i, t in enumerate(ORG):
        st.radio(t, list(NIV), index=None, format_func=lambda v: f"{v} · {NIV[v]}", horizontal=True, key=f"s_o{i}")
    st.text_area("¿Qué te ayuda a concentrarte o terminar tus tareas?", key="s_ayuda")
    st.text_area("¿Hay algo que te dificulte aprender o participar en clase y que quisieras que la escuela supiera?", key="s_dif")
    if st.button("Entregar", type="primary"):
        est = {"c": [S.get(f"s_c{i}", "") for i in range(4)], "m": [S.get(f"s_m{i}", "") for i in range(8)]}
        S["_est"] = est
        cambios = {f"w_m{i}": acierta(est["m"][i], m[1]) for i, m in enumerate(MATES)}
        cambios.update({f"w_o{i}": S[f"s_o{i}"] for i in range(8) if S.get(f"s_o{i}") is not None})
        cambios["w_ayuda"], cambios["w_dif"] = S.get("s_ayuda", ""), S.get("s_dif", "")
        S.update(cambios)
        store.update(cambios)
        S["_entregado"] = True
        st.rerun()
    st.stop()

# ================= MODO APLICADOR =================
st.title("Cuadernillo de exploración educativa")
st.caption("Secundaria Emiliano Zapata · 12 a 14 años · Uso educativo interno y confidencial")
st.info("Herramienta para la persona aplicadora. No diagnostica: el instrumento no está estandarizado ni validado "
        "clínicamente. Los datos solo viven en esta sesión; descarga el reporte antes de cerrar.")
est = S.get("_est")

st.header("Datos de la aplicación")
S.setdefault("w_edad", 12)
S.setdefault("w_fecha", date.today())
c1, c2 = st.columns(2)
folio = c1.text_input("Folio del estudiante", key="w_folio")
edad = c2.number_input("Edad", 10, 16, key="w_edad")
grado = c1.text_input("Grado y grupo", key="w_grado")
fecha = c2.date_input("Fecha de aplicación", key="w_fecha")
aplicador = st.text_input("Aplicador(a)", key="w_aplicador")
st.text_input("PIN para volver desde el modo estudiante", key="w_pin")
if st.button("▶ Iniciar modo estudiante (actividades 3, 5 y 6)"):
    S["_modo"], S["_entregado"], S["_est"] = "est", False, None
    for k in [k for k in S if k.startswith("s_")]:
        del S[k]
    st.rerun()
if est:
    st.success("El estudiante ya entregó las actividades 3, 5 y 6; sus respuestas aparecen abajo.")

st.header("Actividad 1. Atención visual")
st.caption("Hay 25 letras A en total. Cuenta en la hoja del estudiante.")
a1, a2 = st.columns(2)
aciertos = a1.number_input("Aciertos (A tachadas)", 0, 25, key="w_aciertos")
falsos = a2.number_input("Falsos positivos (otras letras tachadas)", 0, 200, key="w_falsos")
omisiones = 25 - aciertos
st.write(f"Omisiones: **{omisiones}** de 25")

st.header("Actividad 2. Escuchar y recordar")
st.markdown("**Parte A.** Palabras recordadas")
recordadas = [p for p in PALABRAS if st.checkbox(p, key=f"w_p_{p}")]
intrusiones = st.text_input("Intrusiones (palabras que no estaban)", key="w_intr")
st.markdown("**Parte B.** Acciones ejecutadas correctamente (primera administración)")
acciones_ok = [a for a in ACCIONES if st.checkbox(a, key=f"w_a_{a}")]
errores_2b = st.text_input("Errores cualitativos en la parte B", key="w_err2b")

st.header("Actividad 3. Comprensión lectora")
st.caption("Se aceptan paráfrasis que conserven el sentido.")
compr_ok = []
for i, (q, clave) in enumerate(COMP):
    if est:
        st.write(f"**{q}** → _{est['c'][i] or 'sin respuesta'}_")
    if st.checkbox(f"{i + 1}. Correcta · clave: {clave}", key=f"w_c{i}"):
        compr_ok.append(q)

st.header("Actividad 4. Expresión escrita")
escr_flag = st.checkbox("El texto es poco comprensible o está muy desorganizado", key="w_escr")
expresion = st.text_area("Observaciones (5 a 8 oraciones: ¿qué ocurrió, qué hizo, cómo terminó?)", key="w_expr")

st.header("Actividad 5. Razonamiento y matemáticas")
mates_ok = []
for i, (q, _, clave) in enumerate(MATES):
    if est:
        st.write(f"{i + 1}. {q} → **{est['m'][i] or '—'}**")
    if st.checkbox(f"{i + 1}. Correcta · clave: {clave}", key=f"w_m{i}"):
        mates_ok.append(q)
procedimiento = st.text_input("Procedimientos / estrategias observadas", key="w_proc")

st.header("Actividad 6. Cómo organizo mis tareas")
org = {t: st.radio(t, list(NIV), format_func=lambda v: f"{v} · {NIV[v]}", horizontal=True, key=f"w_o{i}")
       for i, t in enumerate(ORG)}
ayuda = st.text_area("¿Qué le ayuda a concentrarse o terminar sus tareas?", key="w_ayuda")
dificulta = st.text_area("¿Qué le dificulta aprender o participar?", key="w_dif")

st.header("Registro cualitativo del aplicador")
OBS = ["Atención durante la aplicación", "Comprensión de instrucciones y necesidad de apoyos",
       "Lectura, escritura y organización de ideas", "Estrategias de resolución de problemas",
       "Fortalezas observadas", "Factores que pudieron influir (sueño, ansiedad, ausencias, idioma, visión/audición)"]
obs = {k: st.text_area(k, key=f"w_obs{i}") for i, k in enumerate(OBS)}
apoyos = st.multiselect("Apoyos inmediatos que se probarán", APOYOS, key="w_apoyos")

# ---------- Resumen ----------
st.header("Resumen descriptivo")
org_alto = [t for t, v in org.items() if v >= 2]
resumen = pd.DataFrame([
    ["1. Atención visual", f"{aciertos}/25 aciertos · {omisiones} omisiones · {falsos} falsos positivos"],
    ["2A. Recuerdo inmediato", f"{len(recordadas)}/5" + (f" · intrusiones: {intrusiones}" if intrusiones else "")],
    ["2B. Instrucciones", f"{len(acciones_ok)}/5"],
    ["3. Comprensión lectora", f"{len(compr_ok)}/4"],
    ["5. Matemáticas", f"{len(mates_ok)}/8"],
    ["6. Conductas frecuentes o casi siempre", f"{len(org_alto)}/8"],
], columns=["Actividad", "Resultado"])
st.table(resumen)

# ---------- Áreas a explorar ----------
areas = []
ind = []
if omisiones >= U["omisiones"]: ind.append(f"Atención visual: {omisiones} omisiones de 25")
if falsos >= U["falsos_pos"]: ind.append(f"Atención visual: {falsos} falsos positivos (posible actuar sin revisar)")
if len(recordadas) <= U["recuerdo"]: ind.append(f"Recuerdo inmediato bajo: {len(recordadas)}/5")
if len(org_alto) >= U["org_items"]:
    ind.append(f"Organización: {len(org_alto)} de 8 conductas frecuentes (" + "; ".join(t.rstrip(".").lower() for t in org_alto[:3]) + "…)")
if len(ind) >= 2: areas.append((list(AREAS)[0], ind))
ind = []
if len(recordadas) <= U["recuerdo"]: ind.append(f"Recuerdo de palabras: {len(recordadas)}/5")
if len(acciones_ok) <= U["instrucciones"]: ind.append(f"Instrucciones de 5 pasos: {len(acciones_ok)}/5")
if len(ind) >= 2: areas.append((list(AREAS)[1], ind))
ind = []
if len(compr_ok) <= U["comprension"]: ind.append(f"Comprensión lectora: {len(compr_ok)}/4")
if escr_flag: ind.append("Texto de la actividad 4 poco comprensible o desorganizado (según aplicador)")
if ind: areas.append((list(AREAS)[2], ind))
if len(mates_ok) <= U["mates"]:
    areas.append((list(AREAS)[3], [f"Matemáticas: {len(mates_ok)}/8 correctas"]))

st.header("Áreas a explorar (solo para el profesional)")
st.warning("Hipótesis de trabajo, NO un diagnóstico. No mostrar al estudiante. Un diagnóstico requiere entrevista, "
           "historia, pruebas estandarizadas y observación en varios contextos. Los umbrales son heurísticos y se "
           "editan al inicio del archivo.")
if obs[OBS[-1]].strip():
    st.info("Se registraron factores que pudieron influir en el desempeño; interpreta estos resultados con cautela.")
if areas:
    for nombre, indicios in areas:
        explorar, descartar = AREAS[nombre]
        with st.expander(nombre, expanded=True):
            st.markdown("**Por qué aparece:**\n" + "\n".join(f"- {x}" for x in indicios))
            st.markdown(f"**Cómo confirmar o descartar:** {explorar}")
            st.markdown(f"**Descartar primero:** {descartar}")
else:
    st.write("Este cuadernillo no muestra señales que cumplan los criterios de arriba. Eso no descarta nada.")

# ---------- Descargas ----------
L = ["# Reporte de exploración educativa",
     f"Folio: {folio} · Edad: {edad} · Grupo: {grado} · Fecha: {fecha} · Aplicador(a): {aplicador}", "",
     "*Uso educativo interno y confidencial. No es un diagnóstico.*", "", "## Resultados"]
L += [f"- **{r.Actividad}**: {r.Resultado}" for r in resumen.itertuples()]
L += ["", "## Actividad 4", expresion or "-", "", "## Actividad 5. Procedimientos", procedimiento or "-"]
if errores_2b: L += ["", "## Errores en 2B", errores_2b]
L += ["", "## Actividad 6"] + [f"- {t}: {v} ({NIV[v]})" for t, v in org.items()]
L += ["", f"Qué le ayuda: {ayuda or '-'}", f"Qué le dificulta: {dificulta or '-'}", "", "## Registro del aplicador"]
for k, v in obs.items(): L += [f"**{k}:** {v or '-'}", ""]
L += ["## Áreas a explorar (hipótesis de trabajo, no diagnóstico)"]
for nombre, indicios in areas:
    L += [f"### {nombre}"] + [f"- {x}" for x in indicios]
    L += [f"Confirmar/descartar: {AREAS[nombre][0]}", f"Descartar primero: {AREAS[nombre][1]}", ""]
if not areas: L += ["Sin señales que cumplan los criterios. No descarta nada.", ""]
L += ["## Apoyos que se probarán"] + ([f"- {a}" for a in apoyos] or ["-"])

fila = {"folio": folio, "edad": edad, "grupo": grado, "fecha": str(fecha), "a1_aciertos": aciertos,
        "a1_omisiones": omisiones, "a1_falsos_positivos": falsos, "a2a": len(recordadas), "a2b": len(acciones_ok),
        "a3": len(compr_ok), "a5": len(mates_ok), **{f"a6_{i + 1}": v for i, v in enumerate(org.values())},
        "areas_a_explorar": " | ".join(n for n, _ in areas)}
buf = io.StringIO()
pd.DataFrame([fila]).to_csv(buf, index=False)
d1, d2 = st.columns(2)
d1.download_button("Descargar reporte (.md)", "\n".join(L), f"reporte_{folio or 'estudiante'}.md")
d2.download_button("Descargar fila CSV (Excel)", buf.getvalue(), f"datos_{folio or 'estudiante'}.csv")

store.update({k: v for k, v in S.items() if k.startswith("w_")})
