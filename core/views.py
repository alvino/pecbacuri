# ControleRebanho/views.py

from django.shortcuts import  redirect
from django.contrib import messages, auth
from django.views.generic import  TemplateView
from django.contrib.auth.decorators import login_required # Importe o decorador
from django.utils import timezone


from datetime import date, timedelta


from core.services import ZootecnicoService
from financeiro.models import Venda
from financeiro.services import CalculadorIndices
from infraestrutura.models import Pasto
from manejo.services import ReproducaoService
from rebanho.models import Animal, BaixaAnimal
from manejo.models import Reproducao


class ZootecnicoAnalyticsView(TemplateView):
    template_name = 'core/zootecnico.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Chama o serviço e atualiza o contexto de uma vez
        indicadores = ZootecnicoService.obter_indicadores_performance()
        context.update(indicadores)
        
        return context


class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ano_atual = timezone.localdate().year

        # 1. Indicadores Zootécnicos e Alertas
        context.update(ZootecnicoService.obter_indicadores_performance())
        context['alerta_desmame'] = ZootecnicoService.obter_alertas_desmame()
        context['alertas_paricao'] = ZootecnicoService.obter_alertas_paricao()

        # 2. Contagens Rápidas do Rebanho
        animais_vivos = Animal.objects.filter(situacao='VIVO')
        context.update({
            'total_animais': animais_vivos.count(),
            'total_machos': animais_vivos.filter(sexo='M').count(),
            'total_femeas': animais_vivos.filter(sexo='F').count(),
            'alerta_genealogia': animais_vivos.filter(mae__isnull=True).count(),
        })

        # 3. Dados de Distribuição do Ano
        context.update({
            'total_vendido': Venda.objects.filter(animal__situacao='VENDIDO', data_entrada__year=ano_atual).count(),
            'total_baixa': BaixaAnimal.objects.filter(animal__situacao='MORTO', data_baixa__year=ano_atual).count(),
        })

        # 4. Indicadores Financeiros e Reprodutivos
        context.update(ReproducaoService.obter_dados_estacao(ano_atual - 1))
        context.update(CalculadorIndices.obter_estatisticas_financeiras(ano_atual))

        return context


@login_required(login_url='login')
def logout(request):
    try:
        del(request.session['latitude'])
        del(request.session['longitude'])
        del(request.session['current_url'])
    except KeyError:
        pass
    auth.logout(request)
    messages.info(request, "You have been successfully logged out")
    return redirect('dashboard')