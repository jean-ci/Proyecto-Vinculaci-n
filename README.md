# Sistema de Gestión de Proyectos UTA — MVP Fase 1

Implementación inicial de la Fase 1 de la especificación: PostgreSQL, autenticación, roles, catálogos maestros y registro/edición/eliminación de proyectos en estado **Borrador**.

## Tecnologías
- Python 3.12 + FastAPI
- PostgreSQL 16
- SQLAlchemy 2
- JWT en cookie HttpOnly y contraseñas con Argon2
- HTML, CSS y JavaScript
- Docker Compose

## Requisitos
Docker Desktop o Docker Engine con el complemento `docker compose`.

## Inicio rápido
1. Copie `.env.example` como `.env`.
2. Cambie `SECRET_KEY` y `BOOTSTRAP_ADMIN_PASSWORD` en `.env`.
3. Ejecute:

```bash
docker compose up --build -d
```

4. Abra `http://localhost:8000`.
5. Acceso inicial: el correo y contraseña definidos por `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD` en `.env`.

La API interactiva está en `http://localhost:8000/docs` y la comprobación de estado en `http://localhost:8000/health`.

## Roles implementados
- **Administrador:** consulta todos los proyectos, registra usuarios y puede gestionar borradores.
- **Docente:** crea, consulta, edita y elimina únicamente sus propios borradores. Si el usuario tiene carrera asignada, solo registra proyectos de esa carrera.
- **Coordinador de Carrera:** consulta proyectos de su carrera.
- **Coordinador de Vinculación:** consulta proyectos de Vinculación.
- **Coordinador de Investigación:** consulta proyectos de Investigación e Innovación.

Los coordinadores tienen acceso de lectura en esta fase. No se implementa aprobación ni transición de estados.

## Catálogos cargados
Los catálogos se importan automáticamente al iniciar por primera vez la aplicación desde `data/catalogs.json`, generado con los datos del archivo institucional `Formato_Articulacion_RA_Proyectos_INGENIERÍA_INDUSTRIAL_V5.xlsx`: carreras, asignaturas, RA, jerarquía de líneas y sublíneas y escala de contribución. La estructura jerárquica está persistida en tablas relacionadas de PostgreSQL.

## Modelo de datos principal
`roles`, `users`, `careers`, `subjects`, `learning_outcomes`, `domains`, `faculties`, `research_lines`, `research_sublines`, `activity_types`, `contribution_levels`, `projects`, `project_subjects` y `project_outcomes`.

## Alcance y límites de esta entrega
Incluido: autenticación, RBAC, catálogos, CRUD de proyectos en Borrador, relación múltiple con asignaturas y RA, validación de pertenencia de catálogos y persistencia PostgreSQL.

Fuera de esta fase: envío a revisión, rechazo/confirmación, firma electrónica/interna, adjuntos, SMTP, auditoría avanzada, reportes y exportación Excel. No se simula que estas funciones estén disponibles.

## Notas de seguridad para despliegue
- Sustituya las credenciales y `SECRET_KEY` de ejemplo.
- Publique detrás de HTTPS y configure la cookie `secure=True` antes de un despliegue real.
- Configure respaldos de PostgreSQL y migraciones Alembic antes de evolucionar el esquema en producción.
- El arranque actual crea tablas y carga catálogos; para una instalación institucional se recomienda añadir Alembic y pruebas automatizadas antes de producción.

## Reiniciar datos
`docker compose down -v` elimina también el volumen de PostgreSQL y todos los datos; úselo solo si desea reiniciar completamente el entorno.
