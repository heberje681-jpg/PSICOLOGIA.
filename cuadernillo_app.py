import io
import re
import time
import unicodedata
import zlib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Cuadernillo de exploración educativa", page_icon="📋", layout="centered")
try:
    PIN = str(st.secrets["PIN"])
except Exception:
    PIN = "1234"  # cámbialo aquí o en Secrets de Streamlit: PIN = "tu_pin"

# Umbrales HEURÍSTICOS (no validados). Se pueden editar en la pestaña Resultados.
U = {"omisiones": 8, "falsos_pos": 3, "recuerdo": 2, "instrucciones": 3, "comprension": 2, "mates": 4, "org_items": 4}
ULAB = {"omisiones": "Omisiones act. 1 (≥)", "falsos_pos": "Falsos positivos act. 1 (≥)",
        "recuerdo": "Palabras recordadas (≤)", "instrucciones": "Instrucciones 2B (≤)",
        "comprension": "Comprensión lectora (≤)", "mates": "Matemáticas (≤)",
        "org_items": "Conductas de organización frecuentes (≥)"}

FILAS = [f.split() for f in [
    "B A D C A F E A B C D A", "A C B D E A C F A D B E", "D E A B C D A E F B A C", "C A E D B A F C D A E B",
    "B D C A E F A B D C A E", "A E D B A C E D A F B C", "D A F C B A E D C A B E", "E C A D F B A C E D A B"]]
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
COMP = [("¿Qué decidieron hacer los estudiantes?", "crear un huerto escolar", ["huerto"]),
        ("¿Por qué algunas semillas no germinaron?", "recibieron demasiada agua", ["agua"]),
        ("¿Qué hicieron para mejorar los resultados?", "revisaron registros y modificaron el riego", ["riego", "registro"]),
        ("¿Qué enseñanza obtuvieron de la experiencia?", "observar y corregir errores es parte del aprendizaje",
         ["error", "corregir", "observ"])]
MATES = [("Completa la secuencia: 3, 6, 9, 12, ___", ["15"], "15"),
         ("¿Cuál es el resultado de 48 ÷ 6?", ["8"], "8"),
         ("Si un cuaderno cuesta $18, ¿cuánto cuestan 3 cuadernos?", ["54"], "54"),
         ("¿Qué número falta? 5, 10, 20, 40, ___", ["80"], "80"),
         ("Un estudiante leyó 24 páginas el lunes y 17 el martes. ¿Cuántas leyó en total?", ["41"], "41"),
         ("Una actividad empieza a las 10:15 y dura 35 minutos. ¿A qué hora termina?", ["10.50"], "10:50"),
         ("Escribe los números en orden de menor a mayor: 0.8, 0.25, 1.2", ["0.25", "0.8", "1.2"], "0.25, 0.8, 1.2"),
         ("Si 4 paquetes contienen 6 lápices cada uno, ¿cuántos lápices hay en total?", ["24"], "24")]
ORG = ["Olvido qué materiales debo llevar a clase.", "Comienzo una tarea, pero me cuesta terminarla.",
       "Necesito que me recuerden varias veces qué debo hacer.", "Me cuesta organizar una actividad con varios pasos.",
       "Entrego trabajos incompletos por no revisar las instrucciones.",
       "Me cuesta calcular cuánto tiempo necesito para una tarea.",
       "Respondo o actúo antes de pensar qué puede ocurrir.", "Me cuesta volver a una actividad después de una interrupción."]
ORGC = ["Materiales", "Terminar tareas", "Recordatorios", "Organizar pasos", "Instrucciones", "Tiempo", "Impulsividad", "Retomar"]
NIV = {0: "Nunca o casi nunca", 1: "Algunas veces", 2: "Frecuentemente", 3: "Casi siempre"}
APOYOS = ["Instrucciones en pasos cortos", "Repetir o reformular instrucciones", "Apoyo visual / agenda", "Tiempo adicional",
          "Revisión conjunta de tareas", "Lectura guiada o preguntas orales", "Práctica adicional en matemáticas",
          "Menos distractores en el aula", "Entrevista con familia", "Revisión de visión / audición"]
AREAS = {
    "Atención y funciones ejecutivas (explorar TDAH u otras causas)": (
        "Entrevista con familia y docentes, escalas validadas con varios informantes y observación en más de un contexto. "
        "Para considerar TDAH, los síntomas deben iniciar antes de los 12 años y verse en al menos dos ambientes.",
        "sueño, ansiedad o ánimo, visión/audición, ausencias, estrés familiar, método de estudio"),
    "Memoria verbal inmediata y seguimiento de instrucciones": (
        "Prueba estandarizada de memoria de trabajo/verbal y revisión de la audición.",
        "audición, ansiedad, idioma, distracciones durante la actividad"),
    "Lectura, comprensión y escritura (explorar dificultad específica del aprendizaje)": (
        "Valoración psicopedagógica con pruebas estandarizadas e historia escolar. La dificultad debe persistir pese a apoyos y práctica.",
        "visión/audición, rezago escolar o ausencias, idioma, falta de práctica, ansiedad"),
    "Razonamiento y cálculo matemático (explorar dificultad específica en matemáticas)": (
        "Valoración psicopedagógica de cálculo y razonamiento, revisando el procedimiento y no solo el resultado.",
        "ansiedad ante matemáticas, rezago escolar, instrucción previa, errores por falta de atención")}

S = st.session_state


def mostrar(html, alto):  # st.iframe en versiones nuevas; components.html en las anteriores
    if hasattr(st, "iframe"):
        st.iframe(html, height=alto)
    else:
        components.html(html, height=alto)


def norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def acierta(texto, esperado):
    return re.findall(r"\d+(?:[.:]\d+)?", (texto or "").replace(":", ".")) == esperado


def cuenta(s):
    return (f"<div id=t style='font:600 22px sans-serif;color:#fff;background:#2b6cb0;border-radius:8px;padding:8px;"
            f"text-align:center'></div><script>let s={int(s)};const e=document.getElementById('t');"
            "function f(){e.textContent=s>0?'⏱ '+Math.floor(s/60)+':'+String(s%60).padStart(2,'0'):'¡Tiempo! Presiona terminar';"
            "s--;if(s>=-1)setTimeout(f,1000)}f()</script>")


PAL_JS = (f"<div id=p style='font:700 40px sans-serif;color:#fff;background:#2b6cb0;border-radius:10px;padding:12px;"
          f"text-align:center;min-height:56px'></div><script>const w={PALABRAS};let i=0;const p=document.getElementById('p');"
          "function n(){if(i>=w.length){p.textContent='';return}p.textContent=w[i];"
          "try{const u=new SpeechSynthesisUtterance(w[i]);u.lang='es-MX';speechSynthesis.speak(u)}catch(e){}"
          "i++;setTimeout(n,1500)}n()</script>")

tab_ev, tab_re = st.tabs(["📝 Evaluación", "📊 Resultados"])

# ======================= EVALUACIÓN =======================
with tab_ev:
    st.title("Cuadernillo de exploración educativa")
    st.caption("No es un examen: si no sabes una respuesta, déjala en blanco y continúa.")
    c1, c2 = st.columns(2)
    c1.text_input("Nombre", key="w_nombre")
    c2.number_input("Edad", 3, 99, 12, key="w_edad")
    c1.date_input("Fecha de aplicación", key="w_fecha")
    c2.text_input("Aplicador(a)", key="w_aplicador")

    st.header("Actividad 1. Atención visual")
    st.write("Durante 2 minutos, **toca todas las letras A** que encuentres para tacharlas. No toques ninguna otra letra. "
             "Trabaja de izquierda a derecha y de arriba hacia abajo.")
    if st.button("▶ Comenzar (2 minutos)", disabled="_t1" in S):
        S["_t1"] = time.time()
        st.rerun()
    if "_t1" in S:
        ahora = time.time()
        if "_f1" not in S and ahora - S["_t1"] >= 120:
            S["_f1"] = S["_t1"] + 120
        bloq = "_f1" in S
        if not bloq:
            mostrar(cuenta(120 - (ahora - S["_t1"])), 50)
        for r, fila in enumerate(FILAS):
            st.pills(f"Fila {r + 1}", list(range(12)), selection_mode="multi", format_func=lambda i, f=fila: f[i],
                     key=f"w_r{r}", disabled=bloq, label_visibility="collapsed")
        if bloq:
            st.success("Actividad 1 terminada.")
        elif st.button("Terminé la actividad 1"):
            S["_f1"] = time.time()
            st.rerun()

    st.header("Actividad 2. Escuchar y recordar")
    st.write("Presiona el botón **una sola vez** y presta atención a las palabras. Después escribe todas las que recuerdes, en cualquier orden.")
    if st.button("🔊 Escuchar las palabras", disabled=S.get("_oyo", False)):
        S["_oyo"] = True
        mostrar(PAL_JS, 90)
    st.text_area("Palabras que recuerdas", key="w_2a")

    st.header("Actividad 3. Comprensión lectora")
    st.info(TEXTO)
    for i, (q, _, _) in enumerate(COMP):
        st.text_area(f"{i + 1}. {q}", key=f"w_c{i}")

    st.header("Actividad 4. Expresión escrita")
    st.text_area("Escribe un texto de 5 a 8 oraciones sobre una situación en la que tuviste que resolver un problema. "
                 "Explica qué ocurrió, qué hiciste y cómo terminó.", height=220, key="w_a4")

    st.header("Actividad 5. Razonamiento y matemáticas")
    st.caption("Sin calculadora.")
    for i, (q, _, _) in enumerate(MATES):
        st.text_input(f"{i + 1}. {q}", key=f"w_m{i}")

    st.header("Actividad 6. Cómo organizo mis tareas")
    st.caption("Piensa en lo que te sucede normalmente durante las últimas cuatro semanas.")
    for i, t in enumerate(ORG):
        st.radio(t, list(NIV), index=None, format_func=lambda v: f"{v} · {NIV[v]}", horizontal=True, key=f"w_o{i}")
    st.text_area("¿Qué te ayuda a concentrarte o terminar tus tareas?", key="w_ayuda")
    st.text_area("¿Hay algo que te dificulte aprender o participar en clase y que quisieras que la escuela supiera?", key="w_dif")
    if st.button("✅ Terminé la evaluación", type="primary"):
        st.success("¡Gracias por participar! Avisa a tu aplicador(a).")

# ======================= RESULTADOS =======================
with tab_re:
    if not S.get("_ok"):
        p = st.text_input("PIN del profesional", type="password", key="_pin_in")
        if p == PIN:
            S["_ok"] = True
            st.rerun()
        if p:
            st.error("PIN incorrecto.")
    else:
        if st.button("🔒 Bloquear resultados"):
            S["_ok"] = False
            st.rerun()
        nombre, edad, fecha, aplic = S.get("w_nombre", ""), S.get("w_edad", ""), S.get("w_fecha", ""), S.get("w_aplicador", "")
        st.subheader(f"{nombre or 'Sin nombre'} · {edad} años")
        st.caption(f"Fecha: {fecha} · Aplicador(a): {aplic or '-'}")
        with st.expander("⚙️ Umbrales de las áreas a explorar"):
            for k, lab in ULAB.items():
                U[k] = st.number_input(lab, 0, 25, U[k], key=f"u_{k}")

        # Act 1
        sel = [S.get(f"w_r{r}") or [] for r in range(8)]
        hits = [sum(FILAS[r][i] == "A" for i in s) for r, s in enumerate(sel)]
        fps = [len(s) - h for s, h in zip(sel, hits)]
        aciertos, falsos = sum(hits), sum(fps)
        omisiones = 25 - aciertos
        t1 = f"{S['_f1'] - S['_t1']:.0f} s" if "_f1" in S else "no realizada"
        # Act 2A
        toks = list(dict.fromkeys(re.findall(r"[a-z]+", norm(S.get("w_2a", "")))))
        objetivo = {norm(p): p for p in PALABRAS}
        recordadas = [objetivo[t] for t in toks if t in objetivo]
        extras = [t for t in toks if t not in objetivo]
        # Act 5
        mates_ok = [acierta(S.get(f"w_m{i}", ""), MATES[i][1]) for i in range(8)]
        # Act 4
        txt4 = S.get("w_a4", "")
        n_or = len([s for s in re.split(r"[.!?]+", txt4) if s.strip()])
        # Act 6
        org = {t: S.get(f"w_o{i}") for i, t in enumerate(ORG)}
        org_alto = [t for t, v in org.items() if v is not None and v >= 2]

        st.markdown("#### Verificación del profesional")
        st.markdown("**Actividad 2B (en papel):** marca las acciones ejecutadas correctamente")
        acciones_ok = [a for i, a in enumerate(ACCIONES) if st.checkbox(a, key=f"v_b{i}")]
        st.markdown("**Actividad 3:** sugerencia automática por palabras clave; corrige con tu criterio")
        compr_ok = []
        for i, (q, clave, kw) in enumerate(COMP):
            ans = S.get(f"w_c{i}", "")
            auto = any(k in norm(ans) for k in kw)
            if st.checkbox(f"{q} → «{ans or 'sin respuesta'}» (clave: {clave})", value=auto,
                           key=f"v_c{i}_{zlib.crc32(ans.encode())}"):
                compr_ok.append(q)
        escr_flag = st.checkbox("Actividad 4: texto poco comprensible o muy desorganizado", key="v_escr")

        resumen = pd.DataFrame([
            ["1. Atención visual", f"{aciertos}/25 aciertos · {omisiones} omisiones · {falsos} falsos positivos · {t1}"],
            ["2A. Recuerdo inmediato", f"{len(recordadas)}/5" + (f" · otras palabras: {', '.join(extras)}" if extras else "")],
            ["2B. Instrucciones", f"{len(acciones_ok)}/5"],
            ["3. Comprensión lectora", f"{len(compr_ok)}/4"],
            ["4. Expresión escrita", f"{n_or} oraciones · {len(txt4.split())} palabras"],
            ["5. Matemáticas", f"{sum(mates_ok)}/8"],
            ["6. Conductas frecuentes o casi siempre", f"{len(org_alto)}/8"]], columns=["Actividad", "Resultado"])
        st.markdown("#### Resumen")
        st.table(resumen)
        st.markdown("**Porcentaje logrado por actividad**")
        st.bar_chart(pd.DataFrame({"%": [aciertos / 25 * 100, len(recordadas) / 5 * 100, len(acciones_ok) / 5 * 100,
                                          len(compr_ok) / 4 * 100, sum(mates_ok) / 8 * 100]},
                                  index=["1 Atención", "2A Recuerdo", "2B Instrucciones", "3 Comprensión", "5 Matemáticas"]))
        st.markdown("**Actividad 1: aciertos y falsos positivos por fila** (cada fila tiene 3 a 4 letras A)")
        st.bar_chart(pd.DataFrame({"Aciertos": hits, "Falsos positivos": fps}, index=[f"Fila {r + 1}" for r in range(8)]))
        st.markdown("**Actividad 6: frecuencia por conducta (0 a 3)**")
        st.bar_chart(pd.DataFrame({"Nivel": [v if v is not None else 0 for v in org.values()]}, index=ORGC))
        st.markdown("**Actividad 5: respuestas**")
        st.dataframe(pd.DataFrame({"Pregunta": [m[0] for m in MATES], "Respuesta": [S.get(f"w_m{i}", "") for i in range(8)],
                                   "Clave": [m[2] for m in MATES], "✓": ["✔" if o else "✘" for o in mates_ok]}),
                     hide_index=True)
        st.markdown("**Actividad 4: texto del estudiante** (se esperan 5 a 8 oraciones)")
        st.write(txt4 or "_Sin respuesta_")
        st.markdown(f"**Actividad 6, respuestas abiertas.** Le ayuda: {S.get('w_ayuda') or '-'} · Le dificulta: {S.get('w_dif') or '-'}")

        # Áreas a explorar
        areas, nom = [], list(AREAS)
        ind = []
        if omisiones >= U["omisiones"] and "_t1" in S: ind.append(f"Atención visual: {omisiones} omisiones de 25")
        if falsos >= U["falsos_pos"]: ind.append(f"Atención visual: {falsos} falsos positivos (posible actuar sin revisar)")
        if len(recordadas) <= U["recuerdo"] and S.get("_oyo"): ind.append(f"Recuerdo inmediato bajo: {len(recordadas)}/5")
        if len(org_alto) >= U["org_items"]: ind.append(f"Organización: {len(org_alto)} de 8 conductas frecuentes")
        if len(ind) >= 2: areas.append((nom[0], ind))
        ind = []
        if len(recordadas) <= U["recuerdo"] and S.get("_oyo"): ind.append(f"Recuerdo de palabras: {len(recordadas)}/5")
        if len(acciones_ok) <= U["instrucciones"] and acciones_ok: ind.append(f"Instrucciones de 5 pasos: {len(acciones_ok)}/5")
        if len(ind) >= 2: areas.append((nom[1], ind))
        ind = []
        if len(compr_ok) <= U["comprension"]: ind.append(f"Comprensión lectora: {len(compr_ok)}/4")
        if escr_flag: ind.append("Texto de la actividad 4 poco comprensible o desorganizado")
        if ind: areas.append((nom[2], ind))
        if sum(mates_ok) <= U["mates"]: areas.append((nom[3], [f"Matemáticas: {sum(mates_ok)}/8 correctas"]))

        st.markdown("#### Áreas a explorar")
        st.caption("Hipótesis de trabajo para tu criterio profesional; el diagnóstico es del especialista.")
        if areas:
            for n, indicios in areas:
                with st.expander(n, expanded=True):
                    st.markdown("**Por qué aparece:**\n" + "\n".join(f"- {x}" for x in indicios))
                    st.markdown(f"**Cómo confirmar o descartar:** {AREAS[n][0]}")
                    st.markdown(f"**Descartar primero:** {AREAS[n][1]}")
        else:
            st.write("Sin señales que cumplan los criterios. Eso no descarta nada.")

        st.markdown("#### Observaciones y apoyos")
        obs = st.text_area("Observaciones del aplicador (atención, conducta, fortalezas, factores que influyeron)", key="v_obs")
        apoyos = st.multiselect("Apoyos inmediatos que se probarán", APOYOS, key="v_apoyos")

        L = ["# Reporte de exploración educativa", f"Nombre: {nombre} · Edad: {edad} · Fecha: {fecha} · Aplicador(a): {aplic}",
             "", "## Resultados"] + [f"- **{r.Actividad}**: {r.Resultado}" for r in resumen.itertuples()]
        L += ["", "## Actividad 4", txt4 or "-", "", "## Actividad 6"] + [f"- {t}: {v}" for t, v in org.items()]
        L += ["", f"Le ayuda: {S.get('w_ayuda') or '-'}", f"Le dificulta: {S.get('w_dif') or '-'}", "", "## Observaciones", obs or "-", "",
              "## Áreas a explorar (hipótesis de trabajo)"]
        for n, indicios in areas:
            L += [f"### {n}"] + [f"- {x}" for x in indicios] + [f"Confirmar/descartar: {AREAS[n][0]}", f"Descartar primero: {AREAS[n][1]}", ""]
        L += ["## Apoyos"] + ([f"- {a}" for a in apoyos] or ["-"])
        fila = {"nombre": nombre, "edad": edad, "fecha": str(fecha), "a1_aciertos": aciertos, "a1_omisiones": omisiones,
                "a1_falsos_positivos": falsos, "a2a": len(recordadas), "a2b": len(acciones_ok), "a3": len(compr_ok),
                "a5": sum(mates_ok), **{f"a6_{i + 1}": v for i, v in enumerate(org.values())},
                "areas_a_explorar": " | ".join(n for n, _ in areas)}
        buf = io.StringIO()
        pd.DataFrame([fila]).to_csv(buf, index=False)
        d1, d2 = st.columns(2)
        d1.download_button("Descargar reporte (.md)", "\n".join(L), f"reporte_{nombre or 'estudiante'}.md")
        d2.download_button("Descargar fila CSV (Excel)", buf.getvalue(), f"datos_{nombre or 'estudiante'}.csv")
