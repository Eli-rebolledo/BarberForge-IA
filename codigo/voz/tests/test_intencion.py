import pytest

from app import intencion


@pytest.mark.parametrize("texto,esperada", [
    ("¿Cuánto cuesta un corte clásico?", "pregunta"),
    ("¿Abren los domingos?", "pregunta"),
    ("Quiero sacar un turno para barba con Carlos", "agendar"),
    ("Necesito apartar una cita para mañana", "agendar"),
    ("Quiero cancelar mi cita del viernes", "cancelar"),
    ("¿Qué citas tengo?", "mis_citas"),
    ("Quiero poner una queja porque me atendieron mal", "pqrs"),
    ("Hola", "saludo"),
])
def test_reglas(texto, esperada):
    assert intencion.por_reglas(texto)["intencion"] == esperada


def test_tipo_de_pqrs_por_reglas():
    assert intencion.por_reglas("Quiero hacer un reclamo, me cobraron de más")["tipo_pqrs"] == "reclamo"
    assert intencion.por_reglas("Tengo una sugerencia: deberían abrir más temprano")["tipo_pqrs"] == "sugerencia"


def test_sin_ollama_usa_reglas(monkeypatch):
    monkeypatch.setenv("INTENCION_CON_LLM", "true")  # Ollama apunta a un puerto cerrado
    resultado, metodo = intencion.detectar("Quiero cancelar mi cita")
    assert metodo == "reglas" and resultado["intencion"] == "cancelar"


def test_limpia_la_salida_del_llm():
    d = intencion._limpiar({"intencion": "pqrs", "tipo_pqrs": "petición", "resumen": "", "servicio": "null"},
                           "Solicito factura")
    assert d == {"intencion": "pqrs", "tipo_pqrs": "peticion", "resumen": "Solicito factura"}
    with pytest.raises(ValueError):
        intencion._limpiar({"intencion": "borrar_todo"}, "x")


def test_reglas_primero_y_llm_solo_si_es_ambigua(monkeypatch):
    """La nota de voz no espera dos respuestas del modelo: lo claro se resuelve con reglas."""
    monkeypatch.setenv("INTENCION_CON_LLM", "true")
    llamadas = []
    monkeypatch.setattr(intencion, "con_llm", lambda t: llamadas.append(t) or {"intencion": "agendar"})
    assert intencion.detectar("Quiero cancelar mi cita del viernes") == ({"intencion": "cancelar"}, "reglas")
    assert intencion.detectar("¿Cuánto cuesta el corte clásico?")[1] == "reglas"
    assert llamadas == []
    assert intencion.detectar("necesito arreglarme el pelo el viernes por la tarde") == ({"intencion": "agendar"}, "llm")
    assert len(llamadas) == 1
