from django.db import models
from django.urls import reverse
from datetime import date, timedelta 
from django.db.models.functions import Length
from django.utils import timezone 
from decimal import Decimal

from manejo.models import Reproducao

class Lote(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Lote")
    
    # Relação com o Pasto (Para saber onde o lote está)
    pasto_atual = models.ForeignKey(
        'infraestrutura.Pasto', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='lotes_alocados',
        verbose_name="Pasto Atual"
    )
    
    data_entrada = models.DateField(auto_now_add=True, verbose_name="Data de Criação/Entrada no Pasto")
    
    # Define a finalidade do lote (ex: Desmame, Matrizes, Touros)
    finalidade = models.CharField(
        max_length=50, 
        choices=[
            ('MATRIZES', 'Matrizes de Cria'),
            ('BEZERROS', 'Bezerros/Desmama'),
            ('RECRIA', 'Recria (Garrotes/Novilhas)'),
            ('TOUROS', 'Reprodutores'),
            ('OUTRO', 'Outro')
        ],
        verbose_name="Finalidade do Lote"
    )

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Lote de Manejo"
        verbose_name_plural = "Lotes de Manejo"


class AnimalManager(models.Manager):
    def get_queryset(self):
        # Toda busca agora terá essa anotação e ordenação por padrão
        return super().get_queryset().annotate(
            tamanho_id=Length('identificacao')
        ).order_by('tamanho_id', 'identificacao')
    

from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

class Animal(models.Model):
    SITUACAO_CHOICES = [
        ('VIVO', 'Vivo'),
        ('VENDIDO', 'Vendido'),
        ('MORTO', 'Morto (Baixa)'),
        ('SEMEM', 'Semem'),
    ]

    SEXO_CHOICES = [('M', 'Macho'), ('F', 'Fêmea')]

    # === Identificação ===
    identificacao = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Identificação (Brinco)"
    )
    nome = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome")

    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, verbose_name="Sexo")

    situacao = models.CharField(
        max_length=10, 
        choices=SITUACAO_CHOICES, 
        default='VIVO',
        verbose_name="Situação"
    )

    # === Genealogia ===
    mae = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='filhos',
        verbose_name="Mãe"
    )
    pai = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='filhas',
        verbose_name="Pai"
    )

    # === Localização ===
    lote_atual = models.ForeignKey(
        'Lote', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='animais',
        verbose_name="Lote Atual"
    )

    pasto_atual = models.ForeignKey(
        'infraestrutura.Pasto', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='animais_atuais',
        verbose_name="Pasto Atual"
    )

    observacoes = models.TextField(blank=True, verbose_name="Observações")

    # === Campos calculados / cache ===
    peso_atual = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Peso Atual (kg)"
    )
    data_ultima_pesagem = models.DateField(null=True, blank=True)

    objects = AnimalManager()

    class Meta:
        verbose_name = "Animal"
        verbose_name_plural = "Animais"
        ordering = ['identificacao']
        indexes = [
            models.Index(fields=['identificacao']),
            models.Index(fields=['data_nascimento']),
            models.Index(fields=['situacao']),
        ]

    def __str__(self):
        return f"{self.identificacao} {self.nome}"

    def get_absolute_url(self):
        """Retorna a URL para a página de detalhes/ficha do animal."""
        # Altere 'rebanho:animal_detail' para o name exato da sua URL
        return reverse('rebanho:animal_detail', kwargs={'pk': self.pk})

    # === Propriedades melhoradas ===
    @property
    def idade_em_meses(self):
        if not self.data_nascimento:
            return 0
        hoje = date.today()
        delta = hoje - self.data_nascimento
        return (delta.days // 30)  # aproximação boa o suficiente

    @property
    def idade_formatada(self):
        meses = self.idade_em_meses
        anos = meses // 12
        meses_restante = meses % 12
        return f"{anos}a {meses_restante}m" if anos else f"{meses}m"

    def atualizar_peso_cache(self, peso, data):
        """Atualiza cache de peso (chame após criar Pesagem)"""
        self.peso_atual = peso
        self.data_ultima_pesagem = data
        self.save(update_fields=['peso_atual', 'data_ultima_pesagem'])

    def obter_ultimo_peso(self):
        if self.peso_atual is not None:
            return self.peso_atual
        else:
            return 0
        
    @property
    def ua_atual(self):
        peso = self.obter_ultimo_peso()
        
        if peso == 0 or peso is None:
            # Cálculo baseado em idade se não tiver peso
            meses = self.idade_em_meses if hasattr(self, 'idade_em_meses') else self.idade_em_meses
            if meses <= 8:
                return Decimal('0.3')
            elif meses < 12:
                return Decimal('0.4')
            elif meses < 24:
                return Decimal('0.7')
            elif self.sexo == 'F':
                return Decimal('1.0')
            else:
                return Decimal('1.5')
        
        return Decimal(str(peso)) / Decimal('450')



class BaixaAnimal(models.Model):
    CAUSA_CHOICES = (
        ('DOENCA', 'Doença'),
        ('ACIDENTE', 'Acidente'),
        ('VELHICE', 'Velhice'),
        ('PREDACAO', 'Predação'),
        ('OUTRO', 'Outro (Especificar nas Obs.)'),
    )
    
    animal = models.OneToOneField(
        'Animal',
        on_delete=models.PROTECT, 
        limit_choices_to={'situacao': 'VIVO'}, # Só pode dar baixa em animais VIVOS
        verbose_name="Animal"
    )
    data_baixa = models.DateField(verbose_name="Data da Baixa (Morte)")
    causa = models.CharField(
        max_length=10, 
        choices=CAUSA_CHOICES,
        default='DOENCA',
        verbose_name="Causa da Morte"
    )
    observacoes = models.TextField(
        null=True, blank=True,
        verbose_name="Detalhes / Necrópsia"
    )
    
    class Meta:
        verbose_name = "Baixa de Animal"
        verbose_name_plural = "Baixas de Animais"

    def __str__(self):
        return f"Baixa de {self.animal.identificacao} por {self.get_causa_display()}"

