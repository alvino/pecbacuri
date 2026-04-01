# ControleRebanho/views.py

from django.shortcuts import  redirect
from django.contrib import messages, auth
from django.views.generic import  TemplateView
from django.contrib.auth.decorators import login_required # Importe o decorador
from django.utils import timezone
from django.db.models import Sum


from datetime import date, timedelta


from financeiro.models import Venda
from infraestrutura.models import Pasto
from rebanho.models import Animal, BaixaAnimal
from manejo.models import Reproducao


class ZootecnicoAnalyticsView(TemplateView):
    template_name = 'core/zootecnico.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        ano_atual = hoje.year

        # --- DADOS BASE ---
        animais_ativos = Animal.objects.filter(situacao='VIVO')
        total_vivos = animais_ativos.count()
        total_femeas = animais_ativos.filter(sexo='F').count()

        # --- INDICADORES DE PERFORMANCE ---
        # 1. Taxa de Natalidade (Nascimentos no ano vs Matrizes Atuais)
        nascimentos_ano = Animal.objects.filter(data_nascimento__year=ano_atual).count()
        taxa_natalidade = (nascimentos_ano / total_femeas * 100) if total_femeas > 0 else 0

        # 2. Taxa de Mortalidade (Mortes no ano vs Rebanho Ativo)
        mortes_ano = BaixaAnimal.objects.filter(data_baixa__year=ano_atual).count()
        taxa_mortalidade = (mortes_ano / total_vivos * 100) if total_vivos > 0 else 0

        # 3. Eficiência Reprodutiva (Prenhezes confirmadas no ano)
        dgs_ano = Reproducao.objects.filter(data_dg__year=ano_atual)
        taxa_prenhez = (dgs_ano.filter(resultado='P').count() / dgs_ano.count() * 100) if dgs_ano.exists() else 0

        # --- CATEGORIZAÇÃO ETÁRIA ---
        # Exemplo simples de categorias zootécnicas
        bezerros = 0  # 0-12 meses
        sobreanos = 0 # 13-24 meses
        adultos = 0   # > 24 meses

        for animal in animais_ativos:
            if animal.total_meses <= 12: bezerros += 1
            elif animal.total_meses <= 24: sobreanos += 1
            else: adultos += 1

        # --- CÁLCULO DE LOTAÇÃO ---
        area_total_ha = Pasto.objects.aggregate(total_area=Sum('area_hectares'))['total_area'] or 0
        animais_ativos = Animal.objects.filter(situacao='VIVO')
        
        total_ua = 0
        for a in animais_ativos:
            # Equivalência simplificada de Unidade Animal (UA)
            if a.total_meses <= 12:
                total_ua += 0.30  # Bezerro(a)
            elif a.total_meses <= 24:
                total_ua += 0.70  # Novilha/Garrote
            else:
                total_ua += 1.00  # Adulto (Vaca/Touro)

        # Converta a area_total_ha para float para permitir o cálculo com total_ua
        area_float = float(area_total_ha) if area_total_ha else 0

        lotacao_cabecas_ha = (animais_ativos.count() / area_float) if area_float > 0 else 0
        lotacao_ua_ha = (total_ua / area_float) if area_float > 0 else 0

        context.update({
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
        })
        return context


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



        hoje = timezone.localdate()
        ano_atual = hoje.year
        # 3. Dados para o Gráfico de Status Reprodutivo
        # Contagem de resultados de DG (Diagnóstico de Gestação) mais recentes:
        
        # Matrizes Prenhes (resultado='P')
        total_prenhes = Reproducao.objects.filter(
            resultado='P', 
            matriz__situacao='VIVO'
            ).count() 
        
        # Matrizes Vazias (resultado='V')
        total_vazias = Reproducao.objects.filter(
            resultado='V', 
            matriz__situacao='VIVO'
            ).count()

        # Matrizes Aguardando DG ('N' ou sem DG registrado, mas ativas)
        total_aguardando = Reproducao.objects.filter(
            resultado='N', 
            matriz__situacao='VIVO'
            ).count()
        
        # 4. Dados para o Gráfico de Distribuição do Rebanho
        total_vendido = Venda.objects.filter(
            animal__situacao='VENDIDO',
            data_venda__year=ano_atual
            ).count()
        total_baixa = BaixaAnimal.objects.filter(
            animal__situacao='MORTO',
            data_baixa__year=ano_atual
            ).count()
        
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
    return redirect('dashboard')