from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def obtener_resumen_cunas(request):
    data = {
        "estadisticas": {
            "total_cunas": "3 / 10",
            "bebes_monitoreados": 3,
            "alertas_activas": 1
        },
        "cunas": [
            {
                "id": "01",
                "nombre": "Sofía García",
                "edad": "2 meses",
                "sexo": "Femenino",
                "medico": "Dra. María López",
                "ritmo_cardiaco": 125,
                "spo2": 98,
                "estado": "Dormido",
                "canula_ok": True,
                "via_iv_ok": True,
                "alerta": "normal"
            },
            {
                "id": "02",
                "nombre": "Lucas Martínez",
                "edad": "1 mes",
                "sexo": "Masculino",
                "medico": "Dra. María López",
                "ritmo_cardiaco": 132,
                "spo2": 97,
                "estado": "Despierto",
                "canula_ok": True,
                "via_iv_ok": False,
                "alerta": "critica"
            }
        ]
    }
    return Response(data)