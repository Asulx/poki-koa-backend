# Poki Koa — Sistema de Monitoreo Neonatal

> **Poki** (niño/hijo) · **Koa** (alegría, estar contento) — Lengua Rapa Nui

Sistema de monitoreo inteligente de cunas neonatales diseñado para supervisar en tiempo real las constantes vitales y parámetros ambientales de recién nacidos en unidades de cuidado. Centraliza alertas tempranas y datos clínicos para el personal médico.

> **Desarrollo**  
> [Guía de Desarrollo e Instalación (DESARROLLO.md)](./DESARROLLO.md).

---

## Historias de Usuario
Todas las historias están registradas como GitHub Issues.

| ID | Nombre | Issue |
|---|---|---|
| US-01 | Formulario de gestion de pacientes | [#1](https://github.com/Asulx/poki-koa-web/issues/15) |
| US-02 | Formulario de gestion de medicamentos | [#2](https://github.com/Asulx/poki-koa-web/issues/17) |
| US-03 | Listado de medicamentos | [#3](https://github.com/Asulx/poki-koa-web/issues/16) |
| US-04 | Listado de pacientes | [#4](https://github.com/Asulx/poki-koa-web/issues/13) |
| US-05 | Busqueda de filtros y pacientes | [#5](https://github.com/Asulx/poki-koa-web/issues/14) |
| US-06 | Graficos interactivos y visualizacion de estadisticas | [#6](https://github.com/Asulx/poki-koa-web/issues/12) |
| US-07 | Vista y logica del modulo de reportes | [#7](https://github.com/Asulx/poki-koa-web/issues/18) |
| US-08 | Exportacion de reportes (PDF y Excel) | [#8](https://github.com/Asulx/poki-koa-web/issues/19) |
| US-09 | Gestion y modificacion de turnos por ADMIN | [#9](https://github.com/Asulx/poki-koa-web/issues/39) |
| US-10 | Navegacion interactiva de Monitor de cuna hacia detalles de bebe | [#10](https://github.com/Asulx/poki-koa-web/issues/40) |


## Requisitos Extrafuncionales
Ver: [ReqExtrafuncionales.md](./ReqExtrafuncionales.md)

## Entidades del Dominio

```mermaid
erDiagram
    MEDICO ||--o{ BEBE : "atiende (medico_a_cargo)"
    BEBE ||--o| CUNA : "ocupa (paciente)"
    BEBE ||--o{ MEDICAMENTO : "recibe (paciente)"
    BEBE ||--o{ PLAN_CUIDADO : "posee (bebe)"
    BEBE ||--o{ ALERTA : "genera (paciente)"

    MEDICO {
        int id PK
        string nombre_completo
        string turno
    }

    BEBE {
        int id PK
        string nombre_completo
        int edad_meses
        string sexo
        float peso
        date fecha_nacimiento
        datetime fecha_ingreso
        text diagnostico
        text plan_cuidados
        int medico_a_cargo_id FK
    }

    CUNA {
        int id PK
        string identificador
        int paciente_id FK
        int ritmo_cardiaco
        int spo2
        float temperatura
        string estado_sueno
        boolean canula_ok
        boolean via_iv_activa
        datetime ultima_actualizacion
    }

    MEDICAMENTO {
        int id PK
        int paciente_id FK
        string nombre
        string dosis
        string via
        time hora
        string estado
    }

    PLAN_CUIDADO {
        int id PK
        int bebe_id FK
        string area_cuidado
        string intervencion
        string frecuencia
        string estado
    }

    ALERTA {
        int id PK
        int paciente_id FK
        string tipo
        string mensaje
        string nivel
        datetime fecha_hora
    }