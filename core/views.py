# ControleRebanho/views.py

from django.shortcuts import  redirect
from django.contrib import messages, auth
from django.views.generic import  TemplateView
from django.contrib.auth.decorators import login_required # Importe o decorador

from datetime import date, timedelta


from financeiro.models import Venda
from rebanho.models import Animal, BaixaAnimal
from manejo.models import Reproducao


class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Total de Animais
        total_animais = Animal.objects.filter(situacao='VIVO').count()
        
        # 2. Divisão por Sexo
        total_machos = Animal.objects.filter(situacao='VIVO', sexo='M').count()
        total_femeas = Animal.objects.filter(situacao='VIVO', sexo='F').count()
        
        alerta_genealogia = Animal.objects.filter(situacao='VIVO', mae__isnull=True).count()

        animais_ativos = Animal.objects.filter(situacao='VIVO')
        
        alerta_desmame = []
        meses_desmame_min = 6
        meses_desmame_max = 8
        
        for animal in animais_ativos:
            if animal.data_nascimento:
            
                if animal.total_meses >= meses_desmame_min and animal.total_meses <= meses_desmame_max:
                    alerta_desmame.append({
                        'identificacao': animal.identificacao,
                        'idade_meses': animal.total_meses,
                        'data_nascimento': animal.data_nascimento
                    })

        today = date.today()
        # Define a janela de alerta: da data atual até 30 dias no futuro
        data_limite = today + timedelta(days=30)
        
        # Filtra registros de reprodução onde:
        # 1. A parição ainda não ocorreu (gestacao_terminada=False, se você tiver esse campo, senão o próximo filtro garante isso)
        # 2. A Data Prevista do Parto (DPP) está no futuro, mas antes da data limite (+30 dias)
        
        alertas_paricao = Reproducao.objects.filter(
            data_parto_prevista__gte=today,          # DPP é hoje ou no futuro
            data_parto_prevista__lte=data_limite     # DPP é nos próximos 30 dias
        ).select_related('matriz') # Otimiza a busca pelo animal

        # Prepara a lista final para o template
        lista_alertas = []
        for reprod in alertas_paricao:
            dias_restantes = reprod.dias_para_parir()
            
            lista_alertas.append({
                'matriz': reprod.animal.identificacao, # ou outro campo de identificação
                'dpp': reprod.data_parto_prevista,
                'dias_restantes': dias_restantes,
                'link_animal': reprod.animal.get_absolute_url() if hasattr(reprod.animal, 'get_absolute_url') else '#',
            })
            
        context['alertas_paricao'] = lista_alertas
        # 3. Dados para o Gráfico de Status Reprodutivo
        # Contagem de resultados de DG (Diagnóstico de Gestação) mais recentes:
        
        # Matrizes Prenhes (resultado='P')
        total_prenhes = Reproducao.objects.filter(resultado='P', matriz__situacao='VIVO').count() 
        
        # Matrizes Vazias (resultado='V')
        total_vazias = Reproducao.objects.filter(resultado='V', matriz__situacao='VIVO').count()

        # Matrizes Aguardando DG ('N' ou sem DG registrado, mas ativas)
        total_aguardando = Reproducao.objects.filter(resultado='N', matriz__situacao='VIVO').count()
        
        # 4. Dados para o Gráfico de Distribuição do Rebanho
        total_vendido = Animal.objects.filter(situacao='VENDIDO').count()
        total_baixa = Animal.objects.filter(situacao='MORTO').count()
        
        context = {
            'total_animais': total_animais,
            'total_machos': total_machos,
            'total_femeas': total_femeas,
            'alerta_genealogia': alerta_genealogia,
            'alerta_desmame': alerta_desmame,

            # Dados do Gráfico Reprodutivo
            'total_prenhes': total_prenhes,
            'total_vazias': total_vazias,
            'total_aguardando': total_aguardando,
            
            # Dados do Gráfico de Distribuição
            'total_vendido': total_vendido,
            'total_baixa': total_baixa,
        }
        
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
    return redirect('login')