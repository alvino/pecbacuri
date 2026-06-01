# core/services.py
from django.db.models import Max, Min, Sum
from django.utils import timezone
from django.db.models.functions import Coalesce
from decimal import Decimal

from .models import CustoAnimalDetalhe, Despesa, RegistroDeCusto, Venda
from manejo.models import Pesagem
from rebanho.models import Animal, BaixaAnimal
from django.db.models.functions import TruncMonth
from collections import defaultdict


def obter_fluxo_de_caixa():
    # 1. Agrega as Entradas (Vendas) por mês
    entradas_query = Venda.objects.annotate(
        mes=TruncMonth('data_entrada')
    ).values('mes').annotate(total=Sum('valor_total')).order_by('mes')

    # 2. Agrega as Saídas (Despesas) por mês
    saidas_query = Despesa.objects.annotate(
        mes=TruncMonth('data_pagamento')
    ).values('mes').annotate(total=Sum('valor_total')).order_by('mes')

    # 3. Organiza os dados em um dicionário para facilitar a mesclagem
    fluxo = defaultdict(lambda: {'entradas': 0, 'saidas': 0, 'saldo': 0})

    for e in entradas_query:
        fluxo[e['mes']]['entradas'] = float(e['total'])

    for s in saidas_query:
        fluxo[s['mes']]['saidas'] = float(s['total'])

    # 4. Calcula o saldo final de cada mês
    fluxo_ordenado = []
    for mes in sorted(fluxo.keys()):
        item = fluxo[mes]
        item['mes'] = mes
        item['saldo'] = item['entradas'] - item['saidas']
        fluxo_ordenado.append(item)

    return fluxo_ordenado


def calcular_performance_rebanho(ano_filtro):
    ganho_total_real = 0
    peso_estimado_ua = 0
    
    # 1. Filtramos apenas animais ativos
    animais_ativos = Animal.objects.filter(situacao='VIVO') 


    for animal in animais_ativos:
        # Buscamos as pesagens deste animal no ano específico
        pesagens_do_bicho = Pesagem.objects.filter(
            animal=animal, 
            data_pesagem__year=ano_filtro
        )

        if pesagens_do_bicho.exists():
            # Se houve pesagem, calculamos o ganho real (Max - Min)
            dados = pesagens_do_bicho.aggregate(
                max_p=Max('peso_kg'), 
                min_p=Min('peso_kg')
            )
            ganho = (dados['max_p'] or 0) - (dados['min_p'] or 0)
            ganho_total_real += ganho
        else:
            
            peso_estimado_ua += (animal.ua_atual * 450)

    return ganho_total_real, peso_estimado_ua


class CalculadorIndices:
    @staticmethod
    def obter_estatisticas_financeiras_zootecnicas(ano_filtro=None):
        # 1. Total de UAs da Fazenda
        animais_ativos = Animal.objects.filter(situacao='VIVO') 
        # IMPORTANTE: Garanta que ua_atual no model seja @property
        total_ua_fazenda = sum(a.ua_atual for a in animais_ativos) or 1

        # 2. Total de Despesas no mês
        ano_atual = ano_filtro if ano_filtro is not None else timezone.now().year
        total_despesas = RegistroDeCusto.objects.filter(data_pagamento__year=ano_atual).aggregate(
            total=Sum('valor_total')
        )['total'] or 0

        # 3. Cálculo do Índice R$ / UA / Mês
        custo_por_ua = float(total_despesas) / total_ua_fazenda

        # 3. Cálculo de Ganho de Peso (Onde estava o erro)
        # Vamos pegar cada animal que foi pesado no ano e subtrair o menor peso do maior peso
        # ganho_total_kg = 0
        # pesagens_ano = Pesagem.objects.filter(data_pesagem__year=ano_filtro)
        
        # # Pegamos os IDs dos animais que passaram pela balança este ano
        # ids_animais_pesados = pesagens_ano.values_list('animal_id', flat=True).distinct()
        
        # for animal_id in ids_animais_pesados:
        #     pesagens_do_bicho = pesagens_ano.filter(animal_id=animal_id)
        #     # Diferença entre o maior peso registrado no ano e o menor
        #     max_p = pesagens_do_bicho.aggregate(Max('peso_kg'))['peso_kg__max'] or 0
        #     min_p = pesagens_do_bicho.aggregate(Min('peso_kg'))['peso_kg__min'] or 0
        #     ganho_total_kg += (max_p - min_p)
        
        ganho_total_real, peso_estimado_ua = calcular_performance_rebanho(ano_filtro)
        ganho_total_kg = ganho_total_real + peso_estimado_ua

        # Transformando quilos ganhos em Arrobas (@)
        total_arrobas = float(ganho_total_kg) / 30

        # 5. Custo da @ Produzida 
        # (Quanto custou cada arroba que "brotou" no pasto através do ganho de peso)
        custo_arroba = float(total_despesas) / total_arrobas if total_arrobas > 0 else 0

        # 6. Produção por UA (Eficiência biológica)
        # Quantas arrobas cada UA produziu no ano
        arrobas_por_ua = total_arrobas / total_ua_fazenda

        return {
            'custo_por_ua': custo_por_ua,
            'custo_arroba': custo_arroba,
            'total_ua': total_ua_fazenda,
            'arrobas_por_ua': arrobas_por_ua,
            'total_despesas': total_despesas,
            'total_arrobas': total_arrobas,
        }
    
    @staticmethod
    def obter_estatisticas_financeiras(ano_filtro=None):
        # CALCULAR MÉTRICAS GERAIS
        
        custos_totais = RegistroDeCusto.objects.filter(
            data_pagamento__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor_total'), Decimal(0))
        )['total']

        receita_vendas = Venda.objects.filter(
            data_entrada__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor_total'), Decimal(0))
        )['total']
        
        

        receitas_totais = receita_vendas 
        lucro_geral = receitas_totais - custos_totais
        
        # 3. LUCRO POR ANIMAL (Detalhamento)
        
        # ... (Mantendo a lógica complexa de animais_saidos_ids e o loop de detalhe_lucratividade) ...
        
        # Identifica animais que saíram (vendidos, abatidos ou mortos) no ano
        animais_saidos_ids = set()
        
        vendas_periodo = Venda.objects.filter(data_entrada__year=ano_filtro)
        for v in vendas_periodo:
            animais_saidos_ids.add(v.animal_id)

        baixas_periodo = BaixaAnimal.objects.filter(data_baixa__year=ano_filtro)
        for b in baixas_periodo:
            animais_saidos_ids.add(b.animal_id)
            
        animais_saidos = Animal.objects.filter(id__in=animais_saidos_ids)
        
        detalhe_lucratividade = []

        for animal in animais_saidos:
            
            custo_acumulado = CustoAnimalDetalhe.objects.filter(
                animal=animal
            ).aggregate(
                total=Coalesce(Sum('valor_alocado'), Decimal(0))
            )['total']
            
            receita_animal = Decimal(0)
            destino = "N/A"
            data_saida = None
            
            # Lógica de Destino (VENDIDO, ABATIDO, MORTO) ...
            if animal.situacao == 'VENDIDO':
                try:
                    venda = Venda.objects.get(animal=animal)
                    receita_animal = venda.valor_total
                    destino = f"Vendido a {venda.origem_pagador}"
                    data_saida = venda.data_entrada
                except Venda.DoesNotExist:
                     destino = "VENDIDO (Registro de Venda Ausente)"
                

            elif animal.situacao == 'MORTO': 
                try:
                    baixa = BaixaAnimal.objects.get(animal=animal)
                    receita_animal = Decimal(0) 
                    destino = f"Morte ({baixa.get_causa_display()})"
                    data_saida = baixa.data_baixa
                except BaixaAnimal.DoesNotExist:
                     destino = "MORTO (Registro de Baixa Ausente)"

            lucro = receita_animal - custo_acumulado
            
            detalhe_lucratividade.append({
                'identificacao': animal.identificacao,
                'link': animal.get_absolute_url(),
                'data_saida': data_saida,
                'destino': destino,
                'custo_acumulado': custo_acumulado,
                'receita_animal': receita_animal,
                'lucro': lucro,
            })
        
        # 4. Adicionar ao Contexto
        return {
            'custos_totais': custos_totais,
            'receitas_totais': receitas_totais,
            'lucro_geral': lucro_geral,
            'detalhe_lucratividade': detalhe_lucratividade,
        }