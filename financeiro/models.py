from django.db import models
from django.utils import timezone 


###########
# FLUXO DE CAIXA E CONTROLE FINANCEIRO
###########


###########
# FLUXO DE ENTRADA (RECEITAS)
###########

# 1. MANTEMOS A CATEGORIA PARA ENTRADAS GERAIS
class CategoriaReceita(models.Model):
    """Categoriza os tipos de receita geral (e.g., Leite, Silagem, Serviços)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    
    class Meta:
        verbose_name = "Categoria de Receita"
        verbose_name_plural = "Categorias de Receitas"
        ordering = ['nome']

    def __str__(self):
        return self.nome


# 2. O MODELO MÃE (A UNIFICAÇÃO)
class FluxoEntrada(models.Model):
    """Modelo base para unificar toda e qualquer entrada de dinheiro na fazenda."""
    
    TIPO_ENTRADA_CHOICES = (
        ('VENDA_ANIMAL', 'Venda de Animal'),
        ('RECEITA_GERAL', 'Receita Geral (Leite, Silagem, etc.)'),
    )

    data_entrada = models.DateField(default=timezone.now, verbose_name="Data da Entrada")
    descricao = models.CharField(max_length=255, verbose_name="Descrição")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total (R$)")
    origem_pagador = models.CharField(max_length=255, verbose_name="Comprador / Pagador")
    tipo_entrada = models.CharField(
        max_length=15, 
        choices=TIPO_ENTRADA_CHOICES, 
        verbose_name="Origem do Fluxo"
    )
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Fluxo de Entrada"
        verbose_name_plural = "Fluxo de Entradas (Receitas)"
        ordering = ['-data_entrada']

    def __str__(self):
        return f"[{self.get_tipo_entrada_display()}] {self.descricao} - R$ {self.valor_total}"


# 3. TRANSFORMAÇÃO DA SUA VENDA ANTIGA EM FILHA
class Venda(FluxoEntrada):  # <-- Herda de FluxoEntrada
    """Venda de animal. Herda os campos base e adiciona os detalhes do animal."""
    
    animal = models.OneToOneField(
        'rebanho.Animal', 
        on_delete=models.PROTECT, 
        limit_choices_to={'situacao': 'VIVO'},
        verbose_name="Animal Vendido"
    )
    peso_venda = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, blank=True,
        verbose_name="Peso de Venda (Kg)"
    )

    class Meta:
        verbose_name = "Venda de Animal"
        verbose_name_plural = "Vendas de Animais"

    def save(self, *args, **kwargs):
        # Automatiza o preenchimento dos dados na tabela mãe
        self.tipo_entrada = 'VENDA_ANIMAL'
        if not self.descricao:
            self.descricao = f"Venda de {self.animal.identificacao}"
        super().save(*args, **kwargs)


# 4. A NOVA RECEITA SEM VÍNCULO COM ANIMAL
class ReceitaGeral(FluxoEntrada):  # <-- Herda de FluxoEntrada
    """Entradas financeiras diversas que não dependem da venda de um animal."""
    
    categoria = models.ForeignKey(
        CategoriaReceita, 
        on_delete=models.PROTECT,
        verbose_name="Categoria"
    )

    class Meta:
        verbose_name = "Receita Geral"
        verbose_name_plural = "Receitas Gerais"

    def save(self, *args, **kwargs):
        # Automatiza o preenchimento dos dados na tabela mãe
        self.tipo_entrada = 'RECEITA_GERAL'
        super().save(*args, **kwargs)


#############
# FLUXO DE SAÍDA (DESPESAS, REGISTRO DE CUSTOS, ETC.)   
#############

class FluxoSaida(models.Model):
    """Modelo base para unificar toda e qualquer saída de dinheiro do caixa da fazenda."""
    
    TIPO_SAIDA_CHOICES = (
        ('DESPESA_GERAL', 'Despesa Geral (Administrativa/Operacional)'),
        ('REGISTRO_CUSTO', 'Custo Direto Produção (Alocado a Animal/Pasto)'),
    )

    data_pagamento = models.DateField(default=timezone.now, verbose_name="Data do Pagamento/Custo")
    descricao = models.CharField(max_length=255, verbose_name="Descrição da Saída")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total (R$)")
    tipo_saida = models.CharField(
        max_length=15, 
        choices=TIPO_SAIDA_CHOICES, 
        verbose_name="Origem do Fluxo de Saída"
    )
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações Gerais")

    class Meta:
        verbose_name = "Fluxo de Saída"
        verbose_name_plural = "Fluxo de Saídas (Despesas)"
        ordering = ['-data_pagamento']

    def __str__(self):
        return f"[{self.get_tipo_saida_display()}] {self.descricao} - R$ {self.valor_total}"


# ==========================================
# 2. AUXILIARES E CATEGORIAS
# ==========================================

class CategoriaDespesa(models.Model):
    """Categoriza os tipos de despesa (e.g., Alimentação, Sanidade, Mão de Obra)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    
    class Meta:
        verbose_name = "Categoria de Despesa"
        verbose_name_plural = "Categorias de Despesas"
        ordering = ['nome']

    def __str__(self):
        return self.nome


class TipoCusto(models.Model):
    """Categoriza os tipos de despesas gerenciais (Ex: Vacina, Ração, Mão de Obra)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Tipo de Custo"
        verbose_name_plural = "Tipos de Custos"
      


# ==========================================
# 3. MODELOS FILHOS (HERDANDO DE FLUXOSAIDA)
# ==========================================

class Despesa(FluxoSaida):  # <-- Herda de FluxoSaida
    """Detalhes de uma despesa específica na fazenda (foco no financeiro puro)."""
    
    TIPO_CHOICES = (
        ('FIXA', 'Fixa (Ex: Salário, Aluguel)'),
        ('VARIAVEL', 'Variável (Ex: Ração, Medicamentos, Reparos)'),
    )

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
    registro_de_custo = models.OneToOneField(
        'RegistroDeCusto',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='despesa_associada',
        verbose_name="Registro de Custo Associado"
    )

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"

    def save(self, *args, **kwargs):
        self.tipo_saida = 'DESPESA' # Garante que o tipo seja gravado corretamente
        super().save(*args, **kwargs)


class RegistroDeCusto(FluxoSaida):  # <-- Herda de FluxoSaida
    """Registra uma despesa e a associa a um recurso (animal/pasto) ou ao geral."""
    
    tipo_custo = models.ForeignKey(
        TipoCusto,
        on_delete=models.PROTECT,
        related_name='custos_registrados',
        verbose_name="Categoria do Custo"
    )
    
    # --- Relações Opcionais para Alocação de Custo ---
    animal = models.ForeignKey(
        'rebanho.Animal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='custos_individuais',
        verbose_name="Aplicado ao Animal"
    )
    pasto = models.ForeignKey(
        'infraestrutura.Pasto',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='custos_manejo',
        verbose_name="Aplicado ao Pasto"
    )
    quantidade = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=1,
        verbose_name="Quantidade/Unidade"
    )

    class Meta:
        verbose_name = "Registro de Custo"
        verbose_name_plural = "Registros de Custos"

    def save(self, *args, **kwargs):
        self.tipo_saida = 'REGISTRO_CUSTO'
        super().save(*args, **kwargs)


# ==========================================
# 4. DETALHAMENTO DE ALOCAÇÃO (MANTIDO)
# ==========================================

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
    
    class Meta:
        unique_together = ('registro_de_custo', 'animal')
        verbose_name = "Detalhe de Custo Alocado"
        verbose_name_plural = "Detalhes de Custos Alocados"

    def __str__(self):
        return f"Animal {self.animal.identificacao}: R$ {self.valor_alocado}"