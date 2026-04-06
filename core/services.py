# core/services.py
from django.db.models import Sum
from django.utils import timezone


from infraestrutura.models import Pasto
from manejo.models import Reproducao
from manejo.services import ReproducaoService
from rebanho.models import Animal, BaixaAnimal
    

class ZootecnicoService:
    @staticmethod
    def obter_indicadores_performance():
        hoje = timezone.localdate()
        ano_atual = hoje.year

        # --- DADOS BASE ---
        animais_ativos = Animal.objects.filter(situacao='VIVO')
        total_vivos = animais_ativos.count()
        total_femeas = animais_ativos.filter(sexo='F').count()

        # --- INDICADORES DE PERFORMANCE ---
        
        # 1. Taxa de Natalidade
        nascimentos_ano = Animal.objects.filter(data_nascimento__year=ano_atual).count()
        taxa_natalidade = (nascimentos_ano / total_femeas * 100) if total_femeas > 0 else 0

        # 2. Taxa de Mortalidade
        mortes_ano = BaixaAnimal.objects.filter(data_baixa__year=ano_atual).count()
        taxa_mortalidade = (mortes_ano / total_vivos * 100) if total_vivos > 0 else 0

        # 3. Eficiência Reprodutiva
        indice_reproducao = ReproducaoService.obter_dados_estacao(ano_atual-1)
        total_reproducoes = indice_reproducao['total_servicos']
        prenhezes = indice_reproducao['prenhezes']
        taxa_prenhez = (prenhezes / total_reproducoes * 100) if total_reproducoes > 0 else 0

        # --- CATEGORIZAÇÃO ETÁRIA ---
        # Inicializamos os contadores
        bezerros = 0  # 0-12 meses
        sobreanos = 0 # 13-24 meses
        adultos = 0   # > 24 meses

        for animal in animais_ativos:
            # Assumindo que total_meses é uma property ou campo do model Animal
            meses = animal.total_meses 
            if meses <= 12: 
                bezerros += 1
            elif meses <= 24: 
                sobreanos += 1
            else: 
                adultos += 1

        # --- CÁLCULO DE LOTAÇÃO ---
        area_total_ha = Pasto.objects.aggregate(total_area=Sum('area_hectares'))['total_area'] or 0
        area_float = float(area_total_ha)
        
        # IMPORTANTE: ua_atual deve ser uma @property (sem parênteses na chamada)
        total_ua = sum(a.ua_atual for a in animais_ativos) or 1

        lotacao_cabecas_ha = (total_vivos / area_float) if area_float > 0 else 0
        lotacao_ua_ha = (total_ua / area_float) if area_float > 0 else 0

        return {
            'area_total': area_total_ha,
            'total_ua': round(total_ua, 1),
            'lotacao_cabecas_ha': round(lotacao_cabecas_ha, 2),
            'lotacao_ua_ha': round(lotacao_ua_ha, 2),
            
            'ano_atual': ano_atual,
            'taxa_natalidade': round(taxa_natalidade, 1),
            'taxa_mortalidade': round(taxa_mortalidade, 1),
            'taxa_prenhez': round(taxa_prenhez, 1),
            'nascimentos_ano': nascimentos_ano,
            'mortes_ano': mortes_ano,
            'comp_bezerros': bezerros,
            'comp_sobreanos': sobreanos,
            'comp_adultos': adultos,
            'total_vivos': total_vivos,
        }