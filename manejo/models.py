from django.db import models
from datetime import timedelta 
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone 

class TarefaManejo(models.Model):
    TIPO_CHOICES = [
        ('VA', 'Vacinação / Vermifugação'),
        ('RO', 'Rodízio de Pasto Sugerido'),
        ('GE', 'Geral / Outros'),
    ]
    
    titulo = models.CharField(max_length=200, verbose_name="Título da Tarefa")
    data_prevista = models.DateField(verbose_name="Data Prevista")
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, default='GE', verbose_name="Tipo")
    descricao = models.TextField(blank=True, null=True, verbose_name="Detalhes")
    animal = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Animal (opcional)")
    pasto = models.ForeignKey(
        'infraestrutura.Pasto', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Pasto (opcional)")
    concluida = models.BooleanField(default=False, verbose_name="Concluída")

    def __str__(self):
        return f"{self.titulo} ({self.data_prevista})"

    class Meta:
        verbose_name = "Tarefa de Manejo"
        verbose_name_plural = "Tarefas de Manejo"
        ordering = ['data_prevista', 'titulo']
        db_table = 'ControleRebanho_tarefamanejo'  # Especifica o nome da tabela no banco de dados


class Reproducao(models.Model):

    # Relacionamento com a Matriz (Fêmea)
    matriz = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.CASCADE, 
        limit_choices_to={'sexo': 'F'}, # Importante: só permite selecionar fêmeas
        related_name='reproducoes_matriz',
        verbose_name="Matriz"
    )
    
    # Informação da Cobertura/Inseminação
    data_cio = models.DateField(verbose_name="Data do Cio / Protocolo")
    escore = models.DecimalField(
        max_digits=2, 
        decimal_places=1, 
        null=True, 
        blank=True, 
        verbose_name="Escore do Cio (1-5)",
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ],
        help_text="Insira um valor entre 1 e 5")
    # Tipo de Manejo00
    tipo = models.CharField(
        max_length=20, 
        choices=[
            ('IA', 'Inseminação Artificial (IA)'),
            ('IATF', 'Inseminação Artificial em Tempo Fixo (IATF)'),
            ('MONTA', 'Monta Natural')
        ],
        default='IATF',
        verbose_name="Tipo de Manejo"
    )

    # Detalhes do Pai (Touro ou Sêmen)
    # Pode ser o próprio Animal (se for monta) ou apenas um nome/código (se for IA)
    touro = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'sexo': 'M'}, # Importante: só permite selecionar machos
        related_name='reproducoes_touro',
        verbose_name="Touro (se for monta)"
    )
    codigo_semen = models.CharField(max_length=50, blank=True, verbose_name="Cód. Sêmen / Marca")

    # Diagnóstico de Gestação (DG)
    data_dg = models.DateField(null=True, blank=True, verbose_name="Data do DG")
    resultado = models.CharField(
        max_length=10, 
        choices=[
            ('P', 'Prenhe'),
            ('V', 'Vazia'),
            ('N', 'Não Verificado')
        ],
        default='N',
        verbose_name="Resultado DG"
    )
    
    # Campo para registrar o bezerro após o parto
    bezerro = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='origem_reproducao',
        verbose_name="Bezerro Nascido"
    )

    data_parto_prevista = models.DateField(
        null=True, blank=True,
        verbose_name="Data Prevista do Parto"
    )

    def __str__(self):
        return f"Reprodução de {self.matriz.identificacao} em {self.data_cio}"
    
    def save(self, *args, **kwargs):
        # 1. Calcula a data prevista do parto (285 dias)
        if self.data_dg:
            # Se houver DG, calcula a partir da DG (mais preciso)
            self.data_parto_prevista = self.data_dg + timedelta(days=285)
        elif self.data_cio:
            # Se não houver DG, calcula a partir da Cobertura (menos preciso)
            self.data_parto_prevista = self.data_cio + timedelta(days=285)
            
        super().save(*args, **kwargs)

    def dias_para_parir(self):
        """ Retorna quantos dias faltam para a parição. """
        if self.data_parto_prevista:
            dias = (self.data_parto_prevista - timezone.localdate()).days
            return dias
        return None
    

    class Meta:
        verbose_name = "Manejo Reprodutivo"
        verbose_name_plural = "Manejos Reprodutivos"
        db_table = 'ControleRebanho_reproducao'  # Especifica o nome da tabela no banco de dados


class TratamentoSaude(models.Model):
    TIPOS = [
        ('VAC', 'Vacina'),
        ('VERM', 'Vermifugação'),
        ('TRAT', 'Tratamento Específico'),
    ]

    animal = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.CASCADE, 
        related_name='tratamentos',
        verbose_name="Animal"
    )
    data_tratamento = models.DateField(verbose_name="Data do Tratamento")
    tipo_tratamento = models.CharField(
        max_length=4, 
        choices=TIPOS, 
        default='VAC',
        verbose_name="Tipo de Tratamento"
    )
    produto = models.CharField(max_length=100, verbose_name="Produto/Medicamento")
    dose = models.CharField(max_length=50, blank=True, verbose_name="Dose/Via")
    descricao = models.TextField(blank=True, verbose_name="Observações")
    data_proximo_tratamento = models.DateField(null=True, blank=True, verbose_name="Próxima Data Prevista")

    def __str__(self):
        return f"{self.get_tipo_tratamento_display()} em {self.animal.identificacao} ({self.data_tratamento})"

    class Meta:
        verbose_name = "Tratamento de Saúde"
        verbose_name_plural = "Tratamentos de Saúde"
        db_table = 'ControleRebanho_tratamentosaude'  # Especifica o nome da tabela no banco de dados


class Pesagem(models.Model):

    animal = models.ForeignKey(
        'rebanho.Animal', 
        on_delete=models.CASCADE, 
        related_name='historico_pesagens',
        verbose_name="Animal"
    )
    data_pesagem = models.DateField(verbose_name="Data da Pesagem")
    peso_kg = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        verbose_name="Peso (Kg)"
    )
    evento = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name="Evento (Ex: Desmama, Anual, Repasse)"
    )

    def __str__(self):
        return f"Pesagem de {self.animal.identificacao} em {self.data_pesagem} ({self.peso_kg} Kg)"

    class Meta:
        ordering = ['data_pesagem']
        verbose_name = "Pesagem"
        verbose_name_plural = "Controle de Peso"
        db_table = 'ControleRebanho_pesagem'  # Especifica o nome da tabela no banco de dados

