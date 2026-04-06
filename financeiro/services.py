# core/services.py
from django.db.models import Sum
from django.utils import timezone
from django.db.models.functions import Coalesce
from decimal import Decimal

from financeiro.models import CustoAnimalDetalhe, RegistroDeCusto, Venda
from manejo.models import Pesagem
from rebanho.models import Animal, BaixaAnimal


class CalculadorIndices:
    @staticmethod
    def obter_estatisticas_financeiras_zootecnicas(ano_filtro=None):
        # 1. Total de UAs da Fazenda
        animais_ativos = Animal.objects.filter(situacao='VIVO') 
        # IMPORTANTE: Garanta que ua_atual no model seja @property
        total_ua_fazenda = sum(a.ua_atual for a in animais_ativos) or 1

        # 2. Total de Despesas no mês
        ano_atual = ano_filtro if ano_filtro is not None else timezone.now().year
        total_despesas = RegistroDeCusto.objects.filter(data_custo__year=ano_atual).aggregate(
            total=Sum('valor')
        )['total'] or 0

        # 3. Cálculo do Índice R$ / UA / Mês
        custo_por_ua = float(total_despesas) / total_ua_fazenda

        # 4. Custo da @ Produzida
        ganho_total_kg = Pesagem.objects.filter(
            data_pesagem__year=ano_atual
        ).aggregate(total=Sum('peso_kg'))['total'] or 0
        
        total_arrobas = float(ganho_total_kg) / 30
        custo_arroba = float(total_despesas) / total_arrobas if total_arrobas > 0 else 0

        return {
            'custo_por_ua': custo_por_ua,
            'custo_arroba': custo_arroba,
            'total_ua': total_ua_fazenda,
            'total_despesas': total_despesas,
            'total_arrobas': total_arrobas,
        }
    
    @staticmethod
    def obter_estatisticas_financeiras(ano_filtro=None):
        # CALCULAR MÉTRICAS GERAIS
        
        custos_totais = RegistroDeCusto.objects.filter(
            data_custo__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor'), Decimal(0))
        )['total']

        receita_vendas = Venda.objects.filter(
            data_venda__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor_total'), Decimal(0))
        )['total']
        
        

        receitas_totais = receita_vendas 
        lucro_geral = receitas_totais - custos_totais
        
        # 3. LUCRO POR ANIMAL (Detalhamento)
        
        # ... (Mantendo a lógica complexa de animais_saidos_ids e o loop de detalhe_lucratividade) ...
        
        # Identifica animais que saíram (vendidos, abatidos ou mortos) no ano
        animais_saidos_ids = set()
        
        vendas_periodo = Venda.objects.filter(data_venda__year=ano_filtro)
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
                    destino = f"Vendido a {venda.comprador}"
                    data_saida = venda.data_venda
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