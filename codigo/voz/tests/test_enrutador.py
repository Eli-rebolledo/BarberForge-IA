from app import enrutador


def test_mensajes_que_entiende_el_chat():
    m = enrutador.mensaje_para_chat
    assert m("Necesito apartar un turno", {"intencion": "agendar", "servicio": "barba", "barbero": "Carlos"}) \
        == "agendar Necesito apartar un turno barba con Carlos"
    assert m("Quiero agendar un corte", {"intencion": "agendar", "servicio": "corte"}) == "Quiero agendar un corte"
    assert m("Ya no puedo ir el viernes", {"intencion": "cancelar"}) == "cancelar cita"
    assert m("¿Qué tengo pendiente?", {"intencion": "mis_citas"}) == "mis citas"
    assert m("¿Cuánto cuesta el combo?", {"intencion": "pregunta"}) == "¿Cuánto cuesta el combo?"


def test_pqrs_que_el_chat_no_reconoceria_lleva_el_tipo():
    m = enrutador.mensaje_para_chat
    assert m("tengo una queja", {"intencion": "pqrs", "tipo_pqrs": "queja"}) == "tengo una queja"
    assert (m("Quisiera que me envíen la factura", {"intencion": "pqrs", "tipo_pqrs": "peticion"})
            == "Petición: Quisiera que me envíen la factura")
    assert (m("Deberían abrir más temprano", {"intencion": "pqrs", "tipo_pqrs": "sugerencia"})
            == "Sugerencia: Deberían abrir más temprano")
