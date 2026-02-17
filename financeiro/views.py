# ControleRebanho/views.py

from django.shortcuts import  redirect
from django.contrib import messages, auth
from django.views.generic import  TemplateView
from django.db.models import  Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal

from rebanho.models import Animal, BaixaAnimal
from .models import  RegistroDeCusto, CustoAnimalDetalhe,  Venda



class DashboardFinanceiroCBV(TemplateView):
    # 1. Defina o template a ser usado
    template_name = 'financeiro/dashboard_financeiro.html'

    def get_context_data(self, **kwargs):
        # Chama a implementação da classe base para obter o contexto
        context = super().get_context_data(**kwargs)
        
        # --- LÓGICA REUTILIZADA DA FBV ---
        
        # 1. CONFIGURAÇÃO DE FILTRO DE TEMPO
        hoje = timezone.localdate()
        ano_filtro = self.request.GET.get('ano', str(hoje.year))
        
        # 2. CALCULAR MÉTRICAS GERAIS
        
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
        context.update({
            'ano_filtro': ano_filtro,
            'anos_disponiveis': range(hoje.year, hoje.year - 5, -1),
            'custos_totais': custos_totais,
            'receitas_totais': receitas_totais,
            'lucro_geral': lucro_geral,
            'detalhe_lucratividade': detalhe_lucratividade,
        })
        
        return context
