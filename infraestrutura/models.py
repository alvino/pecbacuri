from django.db import models



class Pasto(models.Model):
    # Identificação e Informações Básicas
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Pasto/Piquete")
    area_hectares = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Área (Hectares)")
    tipo_capim = models.CharField(max_length=100, blank=True, verbose_name="Tipo de Capim")
    data_ultimo_manejo = models.DateField(null=True, blank=True, verbose_name="Data Último Manejo (Corte/Adubação)")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    capacidade_maxima_ua = models.IntegerField(
        verbose_name="Capacidade Máxima (UA)", 
        help_text="Unidade Animal que o pasto comporta.",
        null=True,  
        blank=True, 
        default=10,
    )


    def __str__(self):
        return self.nome

    def get_animais_no_pasto(self):
        return self.animais_atuais.all()
        
    def get_total_animais(self):
        return self.get_animais_no_pasto().count()

    class Meta:
        verbose_name = "Pasto/Piquete"
        verbose_name_plural = "Pastos/Piquetes"
        db_table = 'ControleRebanho_pasto'


class MovimentacaoPasto(models.Model):
    """Registra a mudança de um animal para um pasto."""
    animal = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.CASCADE, 
        related_name='movimentacoes_pasto'
    )
    pasto_origem = models.ForeignKey(
        'infraestrutura.Pasto', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='saidas_pasto',
        verbose_name="Pasto de Origem"
    )
    pasto_destino = models.ForeignKey(
        'infraestrutura.Pasto', 
        on_delete=models.CASCADE, 
        related_name='entradas_pasto',
        verbose_name="Pasto de Destino"
    )
    data_entrada = models.DateField(
        verbose_name="Data de Entrada"
    )
    data_saida = models.DateField(
        verbose_name="Data de Saída", 
        null=True, blank=True,
        help_text="Deixe em branco se o animal ainda estiver neste pasto."
    )
    motivo = models.CharField(
        max_length=255, 
        blank=True, null=True, 
        help_text="Ex: Rodízio de Pastagem, Tratamento, Venda, etc."
    )

    class Meta:
        verbose_name = "Movimentação de Pasto"
        verbose_name_plural = "Movimentações de Pasto"
        ordering = ['-data_entrada']
        db_table = 'ControleRebanho_movimentacaopasto'

    def __str__(self):
        saida_str = f"até {self.data_saida}" if self.data_saida else " - ATUAL"
        return f"{self.animal.identificacao}: {self.pasto_destino} ({self.data_entrada} {saida_str})"

