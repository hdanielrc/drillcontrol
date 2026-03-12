Instrucciones para subir y ejecutar la plantilla HEADCOUNT

1) Copiar / subir el archivo `HEADCOUNT.xlsx` al servidor

 - Desde tu máquina local (ejemplo):

   scp ~/Descargas/HEADCOUNT.xlsx root@drillcontrol-server-25:/var/www/drillcontrol/app/perforaciones_diamantinas/plantillas/

 - O desde el servidor mover el archivo a la carpeta `plantillas`:

   mv /ruta/origen/HEADCOUNT.xlsx /var/www/drillcontrol/app/perforaciones_diamantinas/plantillas/HEADCOUNT.xlsx

2) Desde el directorio del proyecto en el servidor (ejemplo: `/var/www/drillcontrol/app/perforaciones_diamantinas`) ejecutar:

 - Comprobar que el archivo existe:

   ls -l plantillas/HEADCOUNT.xlsx

 - (Opcional) Crear un commit con el Excel en el repositorio (si quieres versionarlo):

   git add plantillas/HEADCOUNT.xlsx
   git commit -m "Add HEADCOUNT template"
   git push origin main

   Nota: si no deseas versionarlo en Git, solo colócalo en la carpeta `plantillas`.

3) Ejecutar el import en modo dry-run para revisar acciones previstas:

   source venv/bin/activate   # o el comando que uses para activar tu virtualenv
   python scripts/import_headcount_excel.py --dry-run --clear-existing

4) Si el dry-run es correcto, ejecutar la importación real:

   python scripts/import_headcount_excel.py --clear-existing

5) Posibles permisos/errores comunes:

 - Asegúrate que el usuario cuyo proceso corre (p.ej. `www-data` o el usuario con el que trabajas) tenga permisos de lectura en `plantillas/HEADCOUNT.xlsx`.
 - Si el script falla por falta de dependencias en el `venv`, instala `pandas`, `openpyxl` y `xlrd` en ese entorno:

   . venv/bin/activate
   pip install pandas openpyxl xlrd Django==5.0.7

Resumen rápido
- Subir `HEADCOUNT.xlsx` a `plantillas/` (por SCP o mv)
- Opcional: `git add/commit/push` si quieres versionarlo
- Ejecutar dry-run y luego la importación real con `--clear-existing`

Si quieres, puedo añadir el archivo `HEADCOUNT.xlsx` al repo por ti — pero necesito que subas el archivo al entorno donde estoy (o lo arrastres aquí). Si prefieres no guardarlo en Git, sigue las instrucciones de SCP/mv y ejecuta los comandos en el servidor.
