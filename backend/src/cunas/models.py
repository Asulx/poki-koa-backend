from django.db import models

# 1. Modelo para el personal médico
class Medico(models.Model):
    nombre_completo = models.CharField(max_length=150, help_text="Ej: Dra. María López")
    turno = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nombre_completo

# 2. Modelo para los datos del paciente (bebé)
class Bebe(models.Model):
    SEXO_CHOICES = [
        ('F', 'Femenino'),
        ('M', 'Masculino'),
    ]

    nombre_completo = models.CharField(max_length=200, help_text="Ej: Sofía García")
    edad_meses = models.IntegerField(help_text="Edad en meses")
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    
    # Relacionamos al bebé con un médico. Si el médico se borra, el campo queda en null.
    medico_a_cargo = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.nombre_completo

# 3. Modelo para la Cuna y su monitoreo en tiempo real
class Cuna(models.Model):
    ESTADO_SUENO_CHOICES = [
        ('Dormido', 'Dormido'),
        ('Despierto', 'Despierto'),
    ]

    identificador = models.CharField(max_length=20, unique=True, help_text="Ej: Cuna 01")
    
    # OneToOneField asegura que un bebé solo puede estar en una cuna a la vez
    paciente = models.OneToOneField(Bebe, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Signos Vitales
    ritmo_cardiaco = models.IntegerField(null=True, blank=True, help_text="Latidos por minuto (bpm)")
    spo2 = models.IntegerField(null=True, blank=True, help_text="Nivel de oxígeno (%)")
    
    # Estados de los sensores/conexiones
    estado_sueno = models.CharField(max_length=20, choices=ESTADO_SUENO_CHOICES, default='Despierto')
    canula_ok = models.BooleanField(default=True, help_text="¿La cánula está funcionando bien?")
    via_iv_activa = models.BooleanField(default=False, help_text="¿La vía intravenosa está activa?")
    
    # Se actualiza automáticamente cada vez que se guarda un cambio
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Muestra "Cuna 01 - Sofía García" o "Cuna 01 - Vacía"
        nombre_bebe = self.paciente.nombre_completo if self.paciente else 'Vacía'
        return f"{self.identificador} - {nombre_bebe}"