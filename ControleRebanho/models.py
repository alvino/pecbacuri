from django.db import models
from django.urls import reverse
from datetime import date, timedelta 
from django.db.models import Q 
from django.db.models.functions import Length
from django.utils import timezone 
from decimal import Decimal


class CategoriaDespesa(models.Model):
    """Categoriza os tipos de despesa (e.g., Alimentação, Sanidade, Mão de Obra)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    
    class Meta:
        verbose_name = "Categoria de Despesa"
        verbose_name_plural = "Categorias de Despesas"
        ordering = ['nome']

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

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor} ({self.data_pagamento})"


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
    animal = models.ForeignKey('Animal', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Animal (opcional)")
    pasto = models.ForeignKey('Pasto', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Pasto (opcional)")
    concluida = models.BooleanField(default=False, verbose_name="Concluída")

    def __str__(self):
        return f"{self.titulo} ({self.data_prevista})"

    class Meta:
        verbose_name = "Tarefa de Manejo"
        verbose_name_plural = "Tarefas de Manejo"
        ordering = ['data_prevista', 'titulo']


class TipoCusto(models.Model):
    """Categoriza os tipos de despesas (Ex: Vacina, Ração, Mão de Obra)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    descricao = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Categoria de Custo"
        verbose_name_plural = "Categorias de Custos"


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


class MovimentacaoPasto(models.Model):
    """Registra a mudança de um animal para um pasto."""
    animal = models.ForeignKey(
        'Animal', 
        on_delete=models.CASCADE, 
        related_name='movimentacoes_pasto'
    )
    pasto_origem = models.ForeignKey(
        'Pasto', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='saidas_pasto',
        verbose_name="Pasto de Origem"
    )
    pasto_destino = models.ForeignKey(
        'Pasto', 
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

    def __str__(self):
        saida_str = f"até {self.data_saida}" if self.data_saida else " - ATUAL"
        return f"{self.animal.identificacao}: {self.pasto_destino} ({self.data_entrada} {saida_str})"


class Lote(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Lote")
    
    # Relação com o Pasto (Para saber onde o lote está)
    pasto_atual = models.ForeignKey(
        Pasto, 
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
    

class Animal(models.Model):
    SITUACAO_CHOICES = (
        ('VIVO', 'Vivo'),
        ('VENDIDO', 'Vendido'),
        ('ABATIDO', 'Abatido'),
        ('MORTO', 'Morto (Baixa)'),
        ('SEMEM', 'Semem'),
    )

    # Identificação e Informações Básicas
    identificacao = models.CharField(max_length=50, unique=True, verbose_name="Identificação")
    nome = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome do Animal")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    sexo = models.CharField(max_length=1, choices=[('M', 'Macho'), ('F', 'Fêmea')], verbose_name="Sexo")
    situacao = models.CharField(
        max_length=10, 
        choices=SITUACAO_CHOICES, 
        default='VIVO',
        verbose_name="Situação do Animal"
    )
    
    # Genealogia (Relações com outros animais)
    mae = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='filhos', verbose_name="Mãe")
    pai = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='filhas', verbose_name="Pai")

    # Informações Adicionais
    observacoes = models.TextField(blank=True, verbose_name="Observações")
     # NOVO CAMPO: Lote
    lote_atual = models.ForeignKey(
        'Lote', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='animais_no_lote',
        verbose_name="Lote Atual"
    )

    pasto_atual = models.ForeignKey(
        'Pasto', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='animais_atuais',
        verbose_name="Pasto Atual"
    )

    objects = AnimalManager()  # Usa o gerenciador customizado
    
    def __str__(self):
        return f"{self.identificacao} {self.nome if self.nome else ''}"

    @property
    def total_meses(self):
        if self.data_nascimento:
            hoje = date.today()
            idade_anos = hoje.year - self.data_nascimento.year
            idade_meses = (hoje.month - self.data_nascimento.month)
            if hoje.day < self.data_nascimento.day:
                idade_meses -= 1
            if idade_meses < 0:
                idade_anos -= 1
                idade_meses += 12

            total_meses = idade_anos * 12 + idade_meses
            return total_meses
        else:
            return 0
        
    @property
    def idade_ano_mes(self):
        if self.data_nascimento:
            hoje = date.today()
            idade_anos = hoje.year - self.data_nascimento.year
            idade_meses = hoje.month - self.data_nascimento.month
            if hoje.day < self.data_nascimento.day:
                idade_meses -= 1
            if idade_meses < 0:
                idade_anos -= 1
                idade_meses += 12
           
            return f"{idade_anos} ano(s) e {idade_meses} mes(es)"
        else:
            return 0
        
    def get_absolute_url(self):
        """ Retorna a URL para a instância do objeto (AnimalDetailView). """
        # O 'pk=self.pk' usa a chave primária para construir a URL
        return reverse('animal_detail', kwargs={'pk': self.pk}) 
        
        # Se você estivesse usando slug, seria:
        # return reverse('animal_detail', kwargs={'animal_slug': self.slug})
        
    # Em models.py dentro da classe Animal
    def ganho_medio_diario(self):
        pesagens = self.pesagens.all().order_by('-data_pesagem')[:2]
        if pesagens.count() == 2:
            p_atual = pesagens[0]
            p_anterior = pesagens[1]
            diff_peso = p_atual.peso - p_anterior.peso
            diff_dias = (p_atual.data_pesagem - p_anterior.data_pesagem).days
            if diff_dias > 0:
                return diff_peso / diff_dias
        return 0
    
    def calcular_gpmd_animal(self, dias_filtro=None):
        """Calcula o GPMD (em kg/dia) com base no histórico de pesagens."""
        pesagens = self.historico_pesagens.all().order_by('data_pesagem')
        
        # Filtra por dias se especificado (Ex: últimos 30 dias)
        if dias_filtro is not None:
            data_limite = timezone.localdate() - timedelta(days=dias_filtro)
            pesagens = pesagens.filter(data_pesagem__gte=data_limite)

        if pesagens.count() < 2:
            return None

        # Simplificando para a média entre a primeira e a última pesagem filtrada
        primeira = pesagens.first()
        ultima = pesagens.last()

        peso_total_ganho = ultima.peso_kg - primeira.peso_kg
        dias = (ultima.data_pesagem - primeira.data_pesagem).days
        
        if dias > 0:
            return peso_total_ganho / Decimal(dias)
        return None

    @property
    def ultimo_custo(self):
        """Retorna a data do último custo alocado."""
        return self.custoanimaldetalhe_set.all().order_by('-data_custo').values_list('data_custo', flat=True).first()

    @property
    def ultima_pesagem(self):
        """Retorna a data da última pesagem."""
        return self.historico_pesagens.all().order_by('-data_pesagem').values_list('data_pesagem', flat=True).first()
    
    # --- NOVO MÉTODO DE LÓGICA DE PARTOS ---
    def save(self, *args, **kwargs):
        # Lógica para garantir que o pasto_atual seja atualizado automaticamente
        if self.pk: # Se o animal já existe
            ultima_movimentacao = self.movimentacoes_pasto.last()
            if ultima_movimentacao and ultima_movimentacao.data_saida is None:
                self.pasto_atual = ultima_movimentacao.pasto_destino
            elif ultima_movimentacao is None:
                 self.pasto_atual = None # Limpa se não houver movimentação
        
        # Chama o método save original
        super().save(*args, **kwargs)

        # A lógica só deve rodar se este animal for um recém-nascido (tem mãe)
        if self.mae and self.data_nascimento:
            # 1. Busca a Reprodução da Matriz (Mãe) que estava Prenhe (P)
            #    e ainda não tem bezerro registrado.
            try:
                evento_parto = self.mae.reproducoes_matriz.get(
                    resultado='P',
                    bezerro__isnull=True
                )
                
                # 2. Se um evento for encontrado:
                #    A. Vincula este bezerro (self) ao evento de Reprodução
                evento_parto.bezerro = self
                
                #    B. Atualiza a data do DG (opcional, mas bom para rastreio)
                #       Se a data do DG for nula, vamos definir a data do parto como a data do DG.
                if evento_parto.data_dg is None:
                    evento_parto.data_dg = self.data_nascimento

                #    C. Salva o registro de Reprodução atualizado
                evento_parto.save()
                
            except Reproducao.DoesNotExist:
                # Caso a matriz não tenha um registro 'Prenhe' sem bezerro, 
                # a lógica segue sem erros.
                pass
            except Reproducao.MultipleObjectsReturned:
                 # Alerta de erro: a matriz está com múltiplos eventos 'Prenhe' abertos.
                 # No admin, isso pode ser corrigido manualmente.
                 print(f"ALERTA: Múltiplos eventos 'Prenhe' abertos para a matriz {self.mae.identificacao}")

    
    class Meta:
        verbose_name = "Animal"
        verbose_name_plural = "Animais"




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


class Venda(models.Model):
    animal = models.OneToOneField(
        'Animal', 
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

    def __str__(self):
        return f"Venda de {self.animal.identificacao} em {self.data_venda}"


class Abate(models.Model):
    animal = models.OneToOneField(
        'Animal', 
        on_delete=models.PROTECT, 
        limit_choices_to={'situacao': 'VIVO'}, # Só pode abater animais VIVOS
        verbose_name="Animal Abatido"
    )
    data_abate = models.DateField(verbose_name="Data do Abate")
    peso_carcaca_quente = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        verbose_name="Peso Carcaça Quente (Kg)"
    )
    rendimento_carcaca = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="Rendimento de Carcaça (%)"
    )
    valor_estimado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Valor Estimado da Carcaça (R$)"
    )
    destino_carcaca = models.CharField(
        max_length=255, 
        verbose_name="Destino (Consumo Próprio, Açougue, etc.)"
    )
    
    class Meta:
        verbose_name = "Abate"
        verbose_name_plural = "Abates"

    def __str__(self):
        return f"Abate de {self.animal.identificacao} em {self.data_abate}"


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
        'Animal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='custos_individuais',
        verbose_name="Aplicado ao Animal"
    )
    
    # 2. Alocação a um Pasto Específico (Ex: Adubação, Cerca)
    pasto = models.ForeignKey(
        'Pasto',
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


class CustoAnimalDetalhe(models.Model):
    """Armazena a porção de um RegistroDeCusto que foi alocada a um Animal."""
    
    registro_de_custo = models.ForeignKey(
        'RegistroDeCusto',
        on_delete=models.CASCADE,
        related_name='detalhes_alocacao',
        verbose_name="Custo Fonte"
    )
    
    animal = models.ForeignKey(
        'Animal',
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


class Reproducao(models.Model):

    # Relacionamento com a Matriz (Fêmea)
    matriz = models.ForeignKey(
        Animal, 
        on_delete=models.CASCADE, 
        limit_choices_to={'sexo': 'F'}, # Importante: só permite selecionar fêmeas
        related_name='reproducoes_matriz',
        verbose_name="Matriz"
    )
    
    # Informação da Cobertura/Inseminação
    data_cio = models.DateField(verbose_name="Data do Cio / Protocolo")
    
    # Tipo de Manejo
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
        Animal, 
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
        Animal, 
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


class TratamentoSaude(models.Model):
    TIPOS = [
        ('VAC', 'Vacina'),
        ('VERM', 'Vermifugação'),
        ('TRAT', 'Tratamento Específico'),
    ]

    animal = models.ForeignKey(
        Animal, 
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


class Pesagem(models.Model):

    animal = models.ForeignKey(
        Animal, 
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

