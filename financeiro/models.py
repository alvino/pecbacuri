from django.db import models
from django.utils import timezone 


class CategoriaDespesa(models.Model):
    """Categoriza os tipos de despesa (e.g., Alimentação, Sanidade, Mão de Obra)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    
    class Meta:
        verbose_name = "Categoria de Despesa"
        verbose_name_plural = "Categorias de Despesas"
        ordering = ['nome']
        db_table = 'ControleRebanho_categoriadespesa'

    def __str__(self):
        return self.nome


class Despesa(models.Model):
    """Detalhes de uma despesa específica na fazenda."""
    
    TIPO_CHOICES = (
        ('FIXA', 'Fixa (Ex: Salário, Aluguel)'),
        ('VARIAVEL', 'Variável (Ex: Ração, Medicamentos, Reparos)'),
    )

    data_pagamento = models.DateField(default=timezone.now, verbose_name="Data do Pagamento")
    descricao = models.CharField(max_length=255, verbose_name="Descrição da Despesa")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total (R$)")
    categoria = models.ForeignKey(
        CategoriaDespesa, 
        on_delete=models.PROTECT,
        verbose_name="Categoria"
    )
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_CHOICES,
        default='VARIAVEL',
        verbose_name="Tipo de Despesa"
    )
    # Linka a despesa ao registro de custo para rastreamento no Dashboard
    registro_de_custo = models.OneToOneField(
        'RegistroDeCusto',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Registro de Custo Associado"
    )

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ['-data_pagamento']
        db_table = 'ControleRebanho_despesa'

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor} ({self.data_pagamento})"


class TipoCusto(models.Model):
    """Categoriza os tipos de despesas (Ex: Vacina, Ração, Mão de Obra)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Categoria de Custo"
        verbose_name_plural = "Categorias de Custos"
        db_table = 'ControleRebanho_tipocusto'


class Venda(models.Model):
    animal = models.OneToOneField(
        'rebanho.Animal', 
        on_delete=models.PROTECT, 
        limit_choices_to={'situacao': 'VIVO'}, # Só pode vender animais VIVOS
        verbose_name="Animal Vendido"
    )
    data_venda = models.DateField(verbose_name="Data da Venda")
    peso_venda = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, blank=True,
        verbose_name="Peso de Venda (Kg)"
    )
    valor_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Valor Total da Venda (R$)"
    )
    comprador = models.CharField(
        max_length=255, 
        verbose_name="Comprador"
    )
    observacoes = models.TextField(
        null=True, blank=True,
        verbose_name="Observações"
    )

    class Meta:
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"
        db_table = 'ControleRebanho_venda'

    def __str__(self):
        return f"Venda de {self.animal.identificacao} em {self.data_venda}"


class RegistroDeCusto(models.Model):
    """Registra uma despesa e a associa a um recurso (animal/pasto) ou ao geral."""
    
    data_custo = models.DateField(verbose_name="Data do Custo")
    
    tipo_custo = models.ForeignKey(
        TipoCusto,
        on_delete=models.PROTECT, # Não permite apagar a categoria se houver custos ligados
        related_name='custos_registrados',
        verbose_name="Categoria do Custo"
    )
    
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor Total (R$)"
    )
    
    descricao = models.TextField(verbose_name="Descrição Detalhada")
    
    # --- Relações Opcionais para Alocação de Custo ---
    
    # 1. Alocação a um Animal Específico (Ex: Compra de medicamento individual)
    animal = models.ForeignKey(
        'rebanho.Animal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='custos_individuais',
        verbose_name="Aplicado ao Animal"
    )
    
    # 2. Alocação a um Pasto Específico (Ex: Adubação, Cerca)
    pasto = models.ForeignKey(
        'infraestrutura.Pasto',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='custos_manejo',
        verbose_name="Aplicado ao Pasto"
    )
    
    # 3. Quantidade (Para custos de aplicação, como dose de vacina)
    quantidade = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=1,
        verbose_name="Quantidade/Unidade"
    )

    def __str__(self):
        return f"R$ {self.valor} ({self.tipo_custo}) em {self.data_custo}"

    class Meta:
        verbose_name = "Registro de Custo"
        verbose_name_plural = "Registros de Custos"
        ordering = ['-data_custo']
        db_table = 'ControleRebanho_registrodecusto'


class CustoAnimalDetalhe(models.Model):
    """Armazena a porção de um RegistroDeCusto que foi alocada a um Animal."""
    
    registro_de_custo = models.ForeignKey(
        'RegistroDeCusto',
        on_delete=models.CASCADE,
        related_name='detalhes_alocacao',
        verbose_name="Custo Fonte"
    )
    
    animal = models.ForeignKey(
        'rebanho.Animal',
        on_delete=models.CASCADE,
        related_name='custos_alocados',
        verbose_name="Animal Alocado"
    )
    
    valor_alocado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Valor Alocado (R$)"
    )
    
    def __str__(self):
        return f"Animal {self.animal.identificacao}: R$ {self.valor_alocado}"

    class Meta:
        unique_together = ('registro_de_custo', 'animal')
        verbose_name = "Detalhe de Custo Alocado"
        verbose_name_plural = "Detalhes de Custos Alocados"
        db_table = 'ControleRebanho_custoanimaldetalhe'

