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
        db_table = 'ControleRebanho_lote'  # Especifica o nome da tabela no banco de dados


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
        'infraestrutura.Pasto', 
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
        db_table = 'ControleRebanho_animal'  # Especifica o nome da tabela no banco de dados


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
        db_table = 'ControleRebanho_baixaanimal'  # Especifica o nome da tabela no banco de dados

    def __str__(self):
        return f"Baixa de {self.animal.identificacao} por {self.get_causa_display()}"

