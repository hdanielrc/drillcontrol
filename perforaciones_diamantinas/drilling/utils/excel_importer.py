import pandas as pd
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Abastecimiento, Contrato, UnidadMedida, TipoComplemento, TipoAditivo

class AbastecimientoExcelImporter:
    """Importador de archivos Excel para abastecimiento con borrado por mes operativo"""
    
    def __init__(self, user):
        self.user = user
        self.success_count = 0
        self.skip_count = 0
        self.deleted_count = 0
        self.errors = []
        self.meses_procesados = set()
        self.contratos_procesados = set()

    def process_excel(self, excel_file, delete_existing=True):
        """Procesar archivo Excel con borrado previo opcional por mes operativo"""
        try:
            # Leer archivo Excel
            df = pd.read_excel(excel_file)
            
            # Validar columnas requeridas
            required_columns = ['MES', 'FECHA', 'CONTRATO', 'DESCRIPCION', 'FAMILIA', 'CANT', 'PRECIO', 'UNIDAD']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'success': False,
                    'error': f'Columnas faltantes: {", ".join(missing_columns)}'
                }
            
            # Procesar en transacción
            with transaction.atomic():
                # Agrupar por mes para borrado selectivo
                if delete_existing:
                    meses_a_borrar = df['MES'].dropna().unique()
                    contratos_afectados = df['CONTRATO'].dropna().unique()
                    
                    for mes in meses_a_borrar:
                        for contrato_nombre in contratos_afectados:
                            try:
                                contrato = Contrato.objects.get(nombre_contrato=contrato_nombre)
                                deleted = Abastecimiento.objects.filter(
                                    mes=str(mes).upper().strip(),
                                    contrato=contrato
                                ).delete()
                                self.deleted_count += deleted[0] if deleted[0] else 0
                            except Contrato.DoesNotExist:
                                continue
                
                # Procesar cada fila
                for index, row in df.iterrows():
                    try:
                        self._process_row(row, index)
                    except Exception as e:
                        self.errors.append(f"Fila {index + 2}: {str(e)}")
                        self.skip_count += 1
            
            return {
                'success': True,
                'success_count': self.success_count,
                'skip_count': self.skip_count,
                'deleted_count': self.deleted_count,
                'errors': self.errors,
                'meses_procesados': list(self.meses_procesados),
                'contratos_procesados': list(self.contratos_procesados),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _process_row(self, row, index):
        """Procesar una fila individual del Excel"""
        # Validar datos requeridos
        if pd.isna(row['MES']) or pd.isna(row['DESCRIPCION']) or pd.isna(row['CANT']):
            raise ValidationError("Faltan datos requeridos (MES, DESCRIPCION, CANT)")
        
        # Obtener o validar contrato
        contrato_nombre = str(row['CONTRATO']).strip()
        try:
            contrato = Contrato.objects.get(nombre_contrato=contrato_nombre)
        except Contrato.DoesNotExist:
            raise ValidationError(f"Contrato '{contrato_nombre}' no existe")
        
        # Validar acceso del usuario al contrato
        if not self.user.can_manage_all_contracts() and contrato != self.user.contrato:
            raise ValidationError(f"Sin permisos para el contrato '{contrato_nombre}'")
        
        # Obtener unidad de medida
        unidad_nombre = str(row.get('UNIDAD', 'UND')).strip()
        unidad, _ = UnidadMedida.objects.get_or_create(
            nombre=unidad_nombre,
            defaults={'simbolo': unidad_nombre}
        )
        
        # Procesar fecha
        try:
            if pd.isna(row.get('FECHA')):
                fecha = datetime.now().date()
            else:
                fecha = pd.to_datetime(row['FECHA']).date()
        except:
            fecha = datetime.now().date()
        
        # Determinar familia
        familia = str(row.get('FAMILIA', 'CONSUMIBLES')).strip().upper()
        if familia not in dict(Abastecimiento.FAMILIA_CHOICES):
            familia = 'CONSUMIBLES'
        
        # Crear registro de abastecimiento
        abastecimiento = Abastecimiento(
            mes=str(row['MES']).strip().upper(),
            fecha=fecha,
            contrato=contrato,
            codigo_producto=str(row.get('CODIGO', '')).strip(),
            descripcion=str(row['DESCRIPCION']).strip(),
            familia=familia,
            serie=str(row.get('SERIE', '')).strip() if pd.notna(row.get('SERIE')) else None,
            unidad_medida=unidad,
            cantidad=Decimal(str(row['CANT'])),
            precio_unitario=Decimal(str(row.get('PRECIO', 0))),
            numero_guia=str(row.get('GUIA', '')).strip(),
            observaciones=str(row.get('OBSERVACIONES', '')).strip()
        )
        
        # Asociar tipos si aplica
        if familia == 'PRODUCTOS_DIAMANTADOS':
            tipo_complemento = self._get_or_create_tipo_complemento(
                str(row.get('TIPO_COMPLEMENTO', 'BROCA')).strip()
            )
            abastecimiento.tipo_complemento = tipo_complemento
        
        elif familia == 'ADITIVOS_PERFORACION':
            tipo_aditivo = self._get_or_create_tipo_aditivo(
                str(row.get('TIPO_ADITIVO', 'BENTONITA')).strip(), 
                unidad
            )
            abastecimiento.tipo_aditivo = tipo_aditivo
        
        # Guardar
        abastecimiento.save()
        
        self.success_count += 1
        self.meses_procesados.add(abastecimiento.mes)
        self.contratos_procesados.add(contrato.nombre_contrato)

    def _get_or_create_tipo_complemento(self, nombre):
        """Obtener o crear tipo de complemento"""
        tipo_complemento, _ = TipoComplemento.objects.get_or_create(
            nombre=nombre,
            defaults={
                'categoria': 'BROCA',
                'descripcion': f'Complemento importado: {nombre}'
            }
        )
        return tipo_complemento

    def _get_or_create_tipo_aditivo(self, nombre, unidad):
        """Obtener o crear tipo de aditivo"""
        tipo_aditivo, _ = TipoAditivo.objects.get_or_create(
            nombre=nombre,
            defaults={
                'categoria': 'BENTONITA',
                'unidad_medida_default': unidad,
                'descripcion': f'Aditivo importado: {nombre}'
            }
        )
        return tipo_aditivo