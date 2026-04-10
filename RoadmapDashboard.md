# Roadmap del Dashboard — Agente Deportivo

> Última revisión: 10 de abril de 2026

---

## 🔴 Alta prioridad — UX crítico

- [x] **1. Tabs en el área principal**  
  Reemplazar el `radio` de modos del sidebar por `st.tabs(["Liga", "Equipo", ...])` en el área principal.  
  Libera espacio lateral, da contexto visual inmediato y elimina el scroll innecesario para llegar al botón de acción.  
  ✅ _Completado — commit `561b566`_

- [x] **2. Auto-invalidación del caché con badge "Informe desactualizado"**  
  Cuando el usuario cambia cualquier parámetro sin pulsar el botón de generar, mostrar un aviso visual indicando que el informe visible puede no corresponderse con la selección actual.  
  Implementación: comparar los parámetros actuales con los del último `_cache_key` activo en `st.session_state`.  
  ✅ _Completado — commit `8c5ccd6`_

- [x] **3. Métricas adaptadas al modo activo**  
  Las 4 columnas superiores son siempre las mismas independientemente del modo seleccionado.  
  - **Liga**: goles totales, goles/jornada, equipos más goleadores, promedio de tarjetas.  
  - **Equipo**: victorias/empates/derrotas, puntos, xG propio vs rival, overperformance.  
  - **Jugador**: G+A, minutos jugados, goles/90, asistencias/90.  
  ✅ _Completado — commit `9a1f146`_

- [x] **4. Tablas con `column_config` y barras de progreso**  
  Sustituir los `st.dataframe` genéricos por versiones con `column_config` de Streamlit:  
  - Barras de progreso en columnas de puntos, goles y posesión.  
  - Porcentajes formateados (p. ej. posesión: `52.3%`).  
  - Búsqueda y filtrado nativos habilitados en tablas largas.  
  ✅ _Completado — commit `a42abf3`_

---

## 🟠 Media prioridad — Riqueza de producto

- [x] **5. Tabla de forma en modo Liga (últimas 5 jornadas)**  
  Mostrar junto a la clasificación una columna o sección con la forma reciente de cada equipo representada con emojis (🟢 victoria · ⚪ empate · 🔴 derrota).  
  Los datos ya están en el CSV; solo requiere un cálculo adicional en `analysis.py` y renderizado en `app.py`.  
  ✅ _Completado — commit `7c3cce7`_

- [x] **6. Gráfico de evolución de puntos en modo Equipo**  
  El visualizador ya genera este gráfico. Mostrarlo de forma prominente en la parte superior de la vista de equipo, antes de las tablas, para dar contexto temporal que las métricas estáticas no ofrecen.  
  ✅ _Completado — commit `100873a`_

- [x] **7. Stats per-90 en modo Jugador**  
  Añadir métricas estándar del análisis moderno calculadas sobre los minutos jugados:  
  - Goles/90 · Asistencias/90 · Tiros/90 · Duelos ganados/90  
  Son más justas que los totales para comparar jugadores con distinto tiempo de juego.  
  ✅ _Completado — commit `73f9299`_

- [x] **8. Cotización de mercado en modo Jugador**  
  Campo de valor de mercado (Transfermarkt / FIFAIndex) integrado en el perfil del jugador.  
  Opciones: scraping ligero bajo demanda, input manual por el operador, o caché propia con actualización periódica.  
  Dato de altísimo valor para el uso de scouting del producto.  
  ✅ _Completado — commit `80c68cd`_

- [x] **9. Radar visual en modo Compare**  
  El visualizador ya genera el radar comparativo entre equipos. Actualmente el modo Compare solo muestra la tabla H2H.  
  Mostrar el radar al inicio de la vista para dar lectura inmediata de fortalezas y debilidades relativas.  
  ✅ _Completado — commit `2076792`_

- [x] **10. Prefetch de escudos al seleccionar equipo**  
  Llamar a `get_team_assets()` en segundo plano en cuanto el usuario cambia el selector de equipo, en lugar de esperar a que se genere el informe.  
  Mejora la percepción de velocidad y evita que el sidebar aparezca sin escudo la primera vez.  
  ✅ _Completado — commit `fac53b2`_

---

## 🟡 Baja prioridad — Pulido y detalles

- [x] **11. URL params para compartir informes**  
  Usar `st.query_params` para serializar la competición, temporada, modo y equipo/jugador seleccionados en la URL.  
  Permite compartir un informe concreto con un enlace directo sin necesidad de configurar nada.  
  ✅ _Completado — commit `51054dd`_

- [x] **12. Timestamp visible en el área principal**  
  Mostrar "Datos analizados el [fecha y hora]" junto al título o debajo de las métricas principales.  
  Coste mínimo, elimina la duda del usuario sobre la frescura del informe mostrado.  
  ✅ _Completado — commit `18a7cb1`_

- [x] **13. Ocultar JSON bruto para usuarios no técnicos**  
  El expander `🗂️ Datos en bruto (JSON)` es ruido para usuarios finales.  
  Mostrarlo solo si `BETA_DEBUG=true` está definido en `.env`, o restringirlo a un rol admin futuro.  
  ✅ _Completado — commit `1ac0adc`_

- [x] **14. Compatibilidad mobile**  
  Añadir `use_container_width=True` a todas las imágenes y limitar el número de columnas a 2 en resoluciones pequeñas.  
  Streamlit no tiene detección de viewport nativa; se puede aproximar con CSS en `st.markdown`.  
  ✅ _Completado — commit pendiente_

- [ ] **15. Modo oscuro consistente en gráficos**  
  Los gráficos generados con matplotlib tienen fondo blanco aunque Streamlit esté en modo oscuro.  
  Solución: detectar el tema activo y pasar `plt.style.use('dark_background')` condicionalmente al visualizador.
