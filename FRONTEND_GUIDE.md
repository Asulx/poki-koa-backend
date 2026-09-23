# Guía de Integración para el Equipo Frontend (React + Vite)

> **Poki Koa — Sistema de Monitoreo Neonatal**  
> Documento técnico y contrato de integración entre el Backend Django REST Framework y el Frontend React.

---

## 1. Puesta en Marcha Rápida del Backend

Para levantar el backend localmente y disponer de una clínica neonatal con datos de prueba realistas:

```bash
# 1. Instalar y sincronizar dependencias en el entorno virtual
uv sync

# 2. Aplicar migraciones a la base de datos SQLite
uv run poki_koa migrate

# 3. Sembrar datos de prueba completos (médicos, cunas, pacientes, alertas y telemetría)
uv run poki_koa seed_data

# 4. Iniciar el servidor de desarrollo en http://127.0.0.1:8000/
uv run poki_koa
```

---

## 2. Documentación Interactiva y Contrato OpenAPI 3.0

El backend expone documentación interactiva generada automáticamente con **OpenAPI 3.0**:

| Recurso | URL | Utilidad para Frontend |
|---|---|---|
| **Swagger UI** | [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/) | Interfaz gráfica interactiva para probar cualquier endpoint en vivo. |
| **Redoc** | [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/) | Documentación limpia y estructurada de consulta de esquemas. |
| **OpenAPI Schema** | [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/) | Especificación técnica en formato YAML/JSON. |

### Generación Automática de Tipos TypeScript

Puedes autogenerar todas las interfaces y tipos TypeScript de tu cliente frontend directamente desde el esquema OpenAPI del backend:

```bash
# Ejecutar en la raíz del proyecto frontend (React):
npx openapi-typescript http://127.0.0.1:8000/api/schema/ -o src/types/api.ts
```

---

## 3. Configuración del Cliente HTTP (Axios / Fetch) y CORS

### Variables de Entorno en el Frontend (`.env`)

En tu proyecto Vite (`poki-koa-web`), define la URL base:

```env
VITE_API_URL=http://127.0.0.1:8000/api
```

### Configuración de Instancia de Axios Recomendada

```typescript
// src/api/client.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});
```

> **CORS Habilitado:** El backend acepta peticiones automáticas cross-origin desde los orígenes habituales de desarrollo: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:5174` y `http://localhost:3000`.

---

## 4. Mapeo de Historias de Usuario a la API REST

A continuación se detalla cómo implementar cada una de las 10 Historias de Usuario (US-01 a US-10) del proyecto consumiendo los endpoints del backend:

---

### US-01: Formulario de Gestión de Pacientes (Crear y Editar)

- **Crear Paciente:** `POST /api/bebes/`
- **Actualizar Paciente:** `PUT /api/bebes/{id}/` o `PATCH /api/bebes/{id}/`

**Payload de ejemplo (`POST /api/bebes/`):**
```json
{
  "nombre_completo": "Sofía García",
  "edad_meses": 1,
  "sexo": "F",
  "peso": 3.2,
  "fecha_nacimiento": "2026-08-25",
  "diagnostico": "Prematurez moderada (33 semanas)",
  "plan_cuidados": "Alimentación enteral mínima c/3h",
  "medico_a_cargo": 1
}
```

**Validaciones del Backend:**
- `peso`: Debe ser un número mayor a `0` (retorna `400 Bad Request` si es `<= 0`).
- `fecha_nacimiento`: No puede ser una fecha futura (retorna `400 Bad Request` con mensaje de error).

---

### US-02 y US-03: Gestión y Listado de Medicamentos

- **Listar Medicamentos:** `GET /api/medicamentos/`
- **Filtrar por Paciente:** `GET /api/medicamentos/?paciente={bebe_id}`
- **Filtrar por Estado:** `GET /api/medicamentos/?estado=Pendiente` (o `Administrado`)
- **Prescribir nuevo Medicamento:** `POST /api/medicamentos/`
- **Acción Rápida Administrar (1 clic):** `POST /api/medicamentos/{id}/administrar/`

**Payload para crear prescripción (`POST /api/medicamentos/`):**
```json
{
  "paciente": 1,
  "nombre": "Ampicilina sódica",
  "dosis": "50 mg/kg",
  "via": "IV",
  "hora": "18:00:00",
  "estado": "Pendiente"
}
```

**Respuesta de la Acción Rápida (`POST /api/medicamentos/1/administrar/`):**
```json
{
  "mensaje": "Medicamento Ampicilina sódica administrado exitosamente",
  "medicamento": {
    "id": 1,
    "paciente_nombre": "Mateo Rodríguez",
    "cuna": "C02",
    "nombre": "Ampicilina sódica",
    "dosis": "50 mg/kg",
    "via": "IV",
    "hora": "18:00:00",
    "estado": "Administrado",
    "paciente": 2
  }
}
```

---

### US-04: Listado de Pacientes

- **Endpoint:** `GET /api/bebes/`
- **Detalle de un Paciente:** `GET /api/bebes/{id}/`

Cada paciente incluye en la respuesta su cuna asignada, signos vitales actuales, medicamentos y alertas:

```json
{
  "id": 1,
  "medico_nombre": "Dra. María López",
  "cuna_identificador": "C01",
  "signos_vitales": {
    "ritmo_cardiaco": 132,
    "spo2": 98,
    "temperatura": 36.8
  },
  "medicamentos": [...],
  "alertas": [...],
  "nombre_completo": "Sofía García",
  "edad_meses": 1,
  "sexo": "F",
  "peso": 3.2,
  "fecha_nacimiento": "2026-08-25",
  "fecha_ingreso": "2026-09-16T10:00:00-03:00",
  "diagnostico": "Prematurez moderada",
  "plan_cuidados": "Alimentación enteral mínima",
  "medico_a_cargo": 1
}
```

---

### US-05: Búsqueda y Filtros de Pacientes

El backend soporta búsqueda de texto completo y filtros específicos por query parameters:

- **Búsqueda por texto (nombre o diagnóstico):**  
  `GET /api/bebes/?search=Sofía`  
  `GET /api/bebes/?search=respiratoria`
- **Filtro por sexo (`F` o `M`):**  
  `GET /api/bebes/?sexo=F`
- **Filtro por médico asignado:**  
  `GET /api/bebes/?medico_a_cargo=1`
- **Combinar filtros y búsqueda:**  
  `GET /api/bebes/?search=García&sexo=F&medico_a_cargo=1`
- **Ordenamiento dinámico:**  
  `GET /api/bebes/?ordering=nombre_completo` (ascendente)  
  `GET /api/bebes/?ordering=-fecha_ingreso` (más recientes primero)  
  `GET /api/bebes/?ordering=-peso`

---

### US-06: Gráficos Interactivos y Visualización de Estadísticas

#### 1. Métricas Consolidadas del Dashboard (Tarjetas Superiores)
- **Endpoint:** `GET /api/dashboard/resumen/`

**Respuesta JSON:**
```json
{
  "cunas_totales": 8,
  "cunas_ocupadas": 6,
  "cunas_disponibles": 2,
  "pacientes_activos": 6,
  "alertas_activas_total": 6,
  "alertas_criticas": 4,
  "alertas_advertencia": 2,
  "medicamentos_pendientes": 6,
  "medicamentos_administrados": 5
}
```

#### 2. Serie Temporal para Gráficos (Recharts / Chart.js)
- **Endpoint:** `GET /api/cunas/{id}/historial/?limit=30`

Retorna las lecturas cronológicas de las constantes vitales listas para graficar:

```json
[
  {
    "id": 101,
    "cuna": 1,
    "cuna_identificador": "C01",
    "ritmo_cardiaco": 130,
    "spo2": 98,
    "temperatura": 36.8,
    "fecha_hora": "2026-09-23T08:00:00-03:00"
  },
  {
    "id": 102,
    "cuna": 1,
    "cuna_identificador": "C01",
    "ritmo_cardiaco": 134,
    "spo2": 97,
    "temperatura": 36.9,
    "fecha_hora": "2026-09-23T08:30:00-03:00"
  }
]
```

---

### US-07 y US-08: Módulo de Reportes y Ficha Clínica

Para armar la vista de reportes por paciente o cuna:

1. Consultar la ficha completa del paciente: `GET /api/bebes/{id}/`
2. Consultar el historial de telemetría de su cuna: `GET /api/cunas/{cuna_id}/historial/?limit=100`
3. Consultar todos los medicamentos y horas de administración: `GET /api/medicamentos/?paciente={id}`
4. Consultar historial de eventos y alertas clínicas: `GET /api/alertas/?paciente={id}`
5. Exportar a PDF / Excel utilizando librerías frontend (ej: `jspdf` / `xlsx`) o consumir los datos consolidados.

---

### US-09: Gestión y Modificación de Turnos

- **Listar Médicos:** `GET /api/medicos/`
- **Filtrar Médicos por Turno:** `GET /api/medicos/?turno=Mañana` (o `Tarde`, `Noche`, `Rotativo`)
- **Modificar Turno de un Médico:** `PATCH /api/medicos/{id}/` con payload `{"turno": "Noche"}`

---

### US-10: Monitor de Cunas Interactivo con Navegación al Bebé

- **Listar Cunas con Estado Clínico en Tiempo Real:** `GET /api/cunas/`
- **Listar Alertas Activas:** `GET /api/alertas/activas/`
- **Resolver una Alerta:** `POST /api/alertas/{id}/resolver/`

Cada elemento del listado de cunas incluye el objeto `paciente_detalle`:
- Si la cuna está **ocupada**: `cuna.paciente_detalle` contiene toda la información del bebé (`id`, `nombre_completo`, `diagnostico`). Permite navegar con React Router a `/pacientes/${cuna.paciente_detalle.id}` al hacer clic en la tarjeta.
- Si la cuna está **disponible**: `cuna.paciente` y `cuna.paciente_detalle` son `null`.

---

## 5. Estrategia de Monitoreo en Tiempo Real (Polling)

Para mantener actualizadas las constantes vitales y alertas en la vista de monitoreo continuo sin sobrecargar la red:

### Ejemplo con React Query (`@tanstack/react-query`)

```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

// Hook para refrescar el estado de las cunas cada 3 segundos
export function useCunas() {
  return useQuery({
    queryKey: ['cunas'],
    queryFn: async () => {
      const response = await api.get('/cunas/');
      return response.data;
    },
    refetchInterval: 3000, // Polling cada 3 segundos
  });
}

// Hook para alertas activas prioritarias
export function useAlertasActivas() {
  return useQuery({
    queryKey: ['alertas', 'activas'],
    queryFn: async () => {
      const response = await api.get('/alertas/activas/');
      return response.data;
    },
    refetchInterval: 3000,
  });
}
```

---

## 6. Modelos y Tipos TypeScript Recomendados

```typescript
export type Sexo = 'F' | 'M';
export type EstadoSueno = 'Dormido' | 'Despierto';
export type EstadoMedicamento = 'Pendiente' | 'Administrado';
export type ViaAdministracion = 'IV' | 'IM' | 'ET' | 'VO';
export type NivelAlerta = 'Info' | 'Advertencia' | 'Critica';
export type TipoAlerta = 'ritmo_cardiaco' | 'spo2' | 'temperatura' | 'canula' | 'otra';

export interface SignosVitales {
  ritmo_cardiaco: number | null;
  spo2: number | null;
  temperatura: number | null;
}

export interface Bebe {
  id: number;
  nombre_completo: string;
  edad_meses: number;
  sexo: Sexo;
  peso: number | null;
  fecha_nacimiento: string | null;
  fecha_ingreso: string;
  diagnostico: string | null;
  plan_cuidados: string | null;
  medico_a_cargo: number | null;
  medico_nombre?: string;
  cuna_identificador?: string | null;
  signos_vitales?: SignosVitales | null;
  medicamentos?: Medicamento[];
  alertas?: Alerta[];
}

export interface Cuna {
  id: number;
  identificador: string;
  paciente: number | null;
  paciente_detalle: Bebe | null;
  ritmo_cardiaco: number | null;
  spo2: number | null;
  temperatura: number | null;
  estado_sueno: EstadoSueno;
  canula_ok: boolean;
  via_iv_activa: boolean;
  ultima_actualizacion: string;
}

export interface Medicamento {
  id: number;
  paciente: number;
  paciente_nombre?: string;
  cuna?: string;
  nombre: string;
  dosis: string;
  via: ViaAdministracion;
  hora: string;
  estado: EstadoMedicamento;
}

export interface Alerta {
  id: number;
  paciente: number | null;
  paciente_nombre?: string | null;
  cuna: number | null;
  cuna_identificador?: string | null;
  tipo: TipoAlerta;
  mensaje: string;
  nivel: NivelAlerta;
  fecha_hora: string;
  activa: boolean;
  valor_leido: number | null;
}

export interface HistorialSigno {
  id: number;
  cuna: number;
  cuna_identificador: string;
  ritmo_cardiaco: number | null;
  spo2: number | null;
  temperatura: number | null;
  fecha_hora: string;
}

export interface DashboardResumen {
  cunas_totales: number;
  cunas_ocupadas: number;
  cunas_disponibles: number;
  pacientes_activos: number;
  alertas_activas_total: number;
  alertas_criticas: number;
  alertas_advertencia: number;
  medicamentos_pendientes: number;
  medicamentos_administrados: number;
}
```

---

## 7. Simulación de Eventos y Telemetría desde Consola

Para probar cómo reacciona la interfaz web ante alertas y cambios en tiempo real, puedes usar el simulador de signos vitales:

```bash
# Inyectar una bradicardia severa en la cuna C01:
python src/manage.py simular_alertas --caso bradicardia_critica --cuna C01

# Inyectar desconexión de cánula de oxígeno en la cuna C02:
python src/manage.py simular_alertas --caso canula_desconectada --cuna C02

# Restablecer los signos a la normalidad (la alerta se autorresuelve automáticamente):
python src/manage.py simular_alertas --caso normal --cuna C01
```
