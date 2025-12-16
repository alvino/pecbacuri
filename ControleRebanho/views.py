# ControleRebanho/views.py

from django.shortcuts import render, redirect
from django.contrib import messages, auth
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.decorators import login_required # Importe o decorador
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, F, Q, Count, Sum, Count, Case, When, IntegerField, ExpressionWrapper, FloatField
from django.db.models.functions import Coalesce
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal

from .models import Animal, TratamentoSaude, Reproducao, Pesagem, Lote, Pasto, RegistroDeCusto, CustoAnimalDetalhe, TarefaManejo, Venda, Abate, BaixaAnimal


from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Animal, RegistroDeCusto, Venda, Abate
from .serializers import AnimalSerializer 
from .filters import AnimalFilter

# -----------------------------------------------
# API - Módulo Básico de Rebanho
# -----------------------------------------------

class AnimalViewSet(viewsets.ModelViewSet):
    # Define o QuerySet base: todos os animais vivos
    queryset = Animal.objects.filter(situacao='VIVO').select_related('pasto_atual') 
    
    # Define o Serializer que será usado
    serializer_class = AnimalSerializer
    
    # Restrição de permissão: apenas usuários logados podem acessar a API
    # permission_classes = [IsAuthenticated] # Descomente em produção!

    # Exemplo de Endpoint customizado (Mapeamento de Rebanho)
    @action(detail=False, methods=['get'])
    def resumo_rebanho(self, request):
        """ Endpoint customizado para o frontend, retorna o resumo do inventário. """
        total_animais = self.queryset.count()
        
        # Agregação por pasto
        resumo_por_pasto = self.queryset.values('pasto_atual__nome').annotate(
            count=Count('pasto_atual__nome')
        ).order_by('pasto_atual__nome')
        
        return Response({
            'total_animais': total_animais,
            'por_pasto': resumo_por_pasto
        })


class AlertaRiscoListView(ListView):
    model = Animal
    template_name = 'pecuaria/alertas_risco.html'
    context_object_name = 'animais_em_risco'
    
    # Exclui animais que já saíram do rebanho
    queryset = Animal.objects.filter(situacao='VIVO')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        animais = context[self.context_object_name]
        animais_em_risco_list = []
        
        # --- Configurações de Limite ---
        HOJE = timezone.localdate()
        DIAS_PESAGEM_LIMITE = 60 # Máximo de dias sem pesagem
        GPMD_MINIMO = Decimal('0.20') # GPMD mínimo aceitável (kg/dia)
        
        # 1. Calcular a média de custo do rebanho para o Alerta de Custo
        avg_custo_anual = CustoAnimalDetalhe.objects.filter(
            registro_de_custo__data_custo__year=HOJE.year
        ).aggregate(
            media=Avg('valor_alocado')
        )['media'] or Decimal(0)
        
        CUSTO_LIMITE = avg_custo_anual * Decimal('1.20') # 20% acima da média

        
        for animal in animais:
            riscos = []
            
            # ----------------------------------------------------
            # Risco 1: GPMD Baixo/Negativo
            # ----------------------------------------------------
            gpmd_30d = animal.calcular_gpmd_animal(dias_filtro=30)
            
            if gpmd_30d is not None and gpmd_30d < GPMD_MINIMO:
                riscos.append(f"GPMD de 30 dias ({gpmd_30d:.2f} kg) está abaixo do mínimo ({GPMD_MINIMO:.2f}).")
            
            # ----------------------------------------------------
            # Risco 2: Perda de Pesagem Recente
            # ----------------------------------------------------
            ultima_pesagem = animal.ultima_pesagem
            if ultima_pesagem is None or (HOJE - ultima_pesagem).days > DIAS_PESAGEM_LIMITE:
                 riscos.append(f"Última pesagem é de {(HOJE - (ultima_pesagem or HOJE)).days} dias atrás. Limite: {DIAS_PESAGEM_LIMITE} dias.")

            # ----------------------------------------------------
            # Risco 3: Alto Custo Acumulado
            # ----------------------------------------------------
            custo_acumulado = CustoAnimalDetalhe.objects.filter(
                animal=animal,
                registro_de_custo__data_custo__year=HOJE.year
            ).aggregate(
                total=Sum('valor_alocado')
            )['total'] or Decimal(0)
            
            if custo_acumulado > CUSTO_LIMITE:
                 riscos.append(f"Custo Acumulado ({custo_acumulado:.2f}) está acima da média do rebanho ({CUSTO_LIMITE:.2f}).")
            
            
            if riscos:
                animais_em_risco_list.append({
                    'animal': animal,
                    'riscos': riscos,
                    'gpmd_recente': gpmd_30d,
                    'custo_acumulado': custo_acumulado,
                })

        context['animais_em_risco'] = animais_em_risco_list
        context['media_custo_rebanho'] = avg_custo_anual
        
        return context


@login_required
def alertas_de_manejo(request):
    hoje = timezone.localdate()
    futuro_proximo = hoje + timedelta(days=90) # Alerta para os próximos 90 dias
    
    alertas = []

    # 1. Alertas de Partos Esperados (Partos Previstos)
    # Filtra registros de reprodução onde o resultado ainda não é conhecido (pendente)
    partos_previstos = Reproducao.objects.filter(
        data_parto_prevista__range=[hoje, futuro_proximo],
        # Supondo que 'PENDENTE' seja a situação inicial do resultado
        # Ajuste o filtro 'resultado' conforme o seu modelo de Reproducao:
        # Q(resultado__isnull=True) | Q(resultado='PE') 
    ).order_by('data_parto_prevista')
    
    for repro in partos_previstos:
        dias_restantes = (repro.data_parto_prevista - hoje).days

        if dias_restantes <= 7:
            status_class = 'list-group-item-danger'
            icon_class = 'fas fa-exclamation-triangle'
            status_text = 'Crítico'
        else:
            status_class = 'list-group-item-warning'
            icon_class = 'fas fa-baby'
            status_text = 'Atenção'

        alertas.append({
            'data': repro.data_parto_prevista,
            'titulo': f"Parto Esperado da Matriz {repro.matriz.identificacao}",
            'tipo': 'Parto',
            'animal_link': repro.matriz.get_absolute_url(),
            'animal_identificacao': repro.matriz.identificacao,
            'dias_restantes': dias_restantes,
            'status_class': status_class,
            'icon_class': icon_class,    
            'status': status_text
        })
        
    # 2. Tarefas de Manejo Agendadas
    tarefas_agendadas = TarefaManejo.objects.filter(
        data_prevista__range=[hoje, futuro_proximo],
        concluida=False
    ).order_by('data_prevista')
    
    for tarefa in tarefas_agendadas:
        dias_restantes = (tarefa.data_prevista - hoje).days
        alertas.append({
            'data': tarefa.data_prevista,
            'titulo': tarefa.titulo,
            'tipo': tarefa.get_tipo_display(),
            'animal_link': tarefa.animal.get_absolute_url() if tarefa.animal else None,
            'dias_restantes': dias_restantes,
            'status': 'Crítico' if dias_restantes <= 7 else 'Atenção'
        })
        
    # 3. Ordenar a lista final por data
    alertas.sort(key=lambda x: x['data'])
    
    context = {
        'alertas': alertas,
        'hoje': hoje,
        'futuro_proximo': futuro_proximo
    }
    
    return render(request, 'pecuaria/alertas_de_manejo.html', context)


@login_required
def relatorio_desempenho_pasto(request):

    # 1. Filtros e Parâmetros Padrão
    hoje = timezone.localdate()
    trinta_dias_atras = hoje - timedelta(days=30)
    
    # Pega os filtros da URL
    pasto_id = request.GET.get('pasto')
    data_inicio = request.GET.get('data_inicio', trinta_dias_atras.strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
    
    pastos = Pasto.objects.all().order_by('nome')
    animais_desempenho = []
    
    # --- CORREÇÃO: Inicialize as variáveis que serão usadas no context! ---
    pasto_selecionado = None
    relatorio_resumo = {}
    

    if pasto_id:
        try:
            pasto_selecionado = Pasto.objects.get(pk=pasto_id)
            
            # 2. Identificar animais que estiveram no pasto durante o período
            # Esta lógica é mais precisa para o desempenho do pasto
            animais_no_pasto = Animal.objects.filter(
                movimentacoes_pasto__pasto_destino=pasto_selecionado,
                movimentacoes_pasto__data_entrada__lte=data_fim
            ).filter(
                Q(movimentacoes_pasto__data_saida__gte=data_inicio) | Q(movimentacoes_pasto__data_saida__isnull=True)
            ).distinct()
            
            total_gpmd = 0
            total_custo = 0
            total_animais = 0
            
            for animal in animais_no_pasto:
                # 3. Calcular GPMD, Peso e Custo para CADA ANIMAL no Período
                
                # a) GPMD Médio no período
                # Filtra as pesagens cuja data_pesagem está entre o período
                pesagens_periodo = animal.pesagens.filter(
                    data_pesagem__range=[data_inicio, data_fim],
                    gpmd__isnull=False
                )
                gpmd_medio = pesagens_periodo.aggregate(Avg('gpmd'))['avg']
                
                # b) Último Peso (para peso médio)
                ultima_pesagem = animal.pesagens.filter(data_pesagem__lte=data_fim).order_by('-data_pesagem').first()
                peso_atual = ultima_pesagem.peso if ultima_pesagem else None
                
                # c) Custo Alocado no Período
                custo_periodo = CustoAnimalDetalhe.objects.filter(
                    animal=animal,
                    registro_de_custo__data_custo__range=[data_inicio, data_fim]
                ).aggregate(total=Sum('valor_alocado'))['total'] or 0.00
                
                if gpmd_medio is not None:
                    total_gpmd += gpmd_medio
                    total_custo += custo_periodo
                    total_animais += 1
                    
                    animais_desempenho.append({
                        'identificacao': animal.identificacao,
                        'link': animal.get_absolute_url(),
                        'gpmd_medio': gpmd_medio,
                        'peso_atual': peso_atual,
                        'custo_periodo': custo_periodo,
                    })

            # 4. Resumo do Pasto/Lote
            if total_animais > 0:
                relatorio_resumo = {
                    'pasto_nome': pasto_selecionado.nome,
                    'total_animais': total_animais,
                    'media_gpmd_lote': total_gpmd / total_animais,
                    'custo_total_lote': total_custo,
                    'custo_medio_animal': total_custo / total_animais,
                }
                
        except Pasto.DoesNotExist:
            pasto_selecionado = None
            
    context = {
        'pastos': pastos,
        'pasto_selecionado': pasto_selecionado,
        'data_inicio_filtro': data_inicio,
        'data_fim_filtro': data_fim,
        'animais_desempenho': animais_desempenho,
        'relatorio_resumo': relatorio_resumo,
    }
    
    return render(request, 'pecuaria/relatorio_desempenho_pasto.html', context)


class DashboardFinanceiroCBV(TemplateView):
    # 1. Defina o template a ser usado
    template_name = 'pecuaria/dashboard_financeiro.html'

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
        
        receita_abates = Abate.objects.filter(
            data_abate__year=ano_filtro
        ).aggregate(
            total=Coalesce(Sum('valor_estimado'), Decimal(0))
        )['total']

        receitas_totais = receita_vendas + receita_abates
        lucro_geral = receitas_totais - custos_totais
        
        # 3. LUCRO POR ANIMAL (Detalhamento)
        
        # ... (Mantendo a lógica complexa de animais_saidos_ids e o loop de detalhe_lucratividade) ...
        
        # Identifica animais que saíram (vendidos, abatidos ou mortos) no ano
        animais_saidos_ids = set()
        
        vendas_periodo = Venda.objects.filter(data_venda__year=ano_filtro)
        for v in vendas_periodo:
            animais_saidos_ids.add(v.animal_id)

        abates_periodo = Abate.objects.filter(data_abate__year=ano_filtro)
        for a in abates_periodo:
            animais_saidos_ids.add(a.animal_id)
            
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
                
            elif animal.situacao == 'ABATIDO':
                try:
                    abate = Abate.objects.get(animal=animal)
                    receita_animal = abate.valor_estimado
                    destino = f"Abate ({abate.destino_carcaca})"
                    data_saida = abate.data_abate
                except Abate.DoesNotExist:
                     destino = "ABATIDO (Registro de Abate Ausente)"

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


class PastoListView(ListView):
    """Lista todos os pastos cadastrados na fazenda."""
    model = Pasto
    template_name = 'pecuaria/pasto_list.html'
    context_object_name = 'pastos'
    ordering = ['nome']


class PastoDetailView(LoginRequiredMixin, DetailView):
    model = Pasto
    template_name = 'pecuaria/pasto_detail.html'
    context_object_name = 'pasto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Animais Atualmente no Pasto (usando o related_name 'animais_atuais')
        context['animais_no_pasto'] = context['pasto'].animais_atuais.all().order_by('identificacao')
        
        # 2. Histórico de Movimentações Recentes (opcional, para um histórico)
        context['movimentacoes_recentes'] = context['pasto'].entradas_pasto.all().order_by('-data_entrada')[:10]
        
        return context


class AnimalListView(ListView):
    model = Animal
    template_name = 'pecuaria/animal_list.html'
    context_object_name = 'animais'
    # Filtra apenas os animais ativos por padrão
    queryset = Animal.objects.filter(situacao='VIVO').order_by('identificacao')
    paginate_by = 25 # Opção para paginar os resultados
    
    def get_queryset(self):
        # 1. Obtém o queryset base (todos os animais)
        queryset = super().get_queryset()
        
        # 2. Cria o objeto Filter com os dados GET (query string) e o queryset
        self.filter = AnimalFilter(self.request.GET, queryset=queryset)
        
        # 3. Retorna o queryset filtrado
        return self.filter.qs
    
    # Adicionando contexto extra (se precisar de contagens ou filtros)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Exemplo de contexto extra para o template:
        context['total_ativo'] = Animal.objects.filter(situacao='VIVO').count()
        context['filter'] = self.filter
        return context
    

class AnimalDetailView(LoginRequiredMixin, DetailView):
    model = Animal
    template_name = 'pecuaria/animal_detail.html'
    context_object_name = 'animal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = self.object
        
        # --- 1. Lógica de Idade ---
        if animal.data_nascimento:
            hoje = date.today()
            idade_dias = (hoje - animal.data_nascimento).days
            context['idade_anos'] = idade_dias // 365
            context['idade_meses'] = (idade_dias % 365) // 30

        # --- 2. Histórico de Pesagem (GPMD) ---
        pesagens = animal.historico_pesagens.all().order_by('-data_pesagem')
        context['pesagens'] = pesagens
        
        # Última Pesagem
        if pesagens.exists():
            context['ultima_pesagem'] = pesagens.first()
            
            # GPMD Médio (Calcula a média de todos os GPMDs registrados)
            gpmd_medio = pesagens.exclude(gpmd__isnull=True).aggregate(media_gpmd=Sum('gpmd') / Count('gpmd'))['media_gpmd']
            context['gpmd_medio'] = gpmd_medio
        else:
            context['ultima_pesagem'] = None
            context['gpmd_medio'] = 0

        # --- 3. Histórico de Movimentação de Pasto ---
        context['movimentacoes_pasto'] = animal.movimentacoes_pasto.all().order_by('-data_entrada')

        # --- 4. Histórico Financeiro (Custo Acumulado) ---
        # Soma todos os detalhes de custo alocados a este animal
        custo_acumulado = animal.custos_alocados.aggregate(total=Sum('valor_alocado'))['total']
        context['custo_acumulado'] = custo_acumulado or 0.00
        
        # Detalhe dos custos (para a tabela)
        context['custos_detalhados'] = animal.custos_alocados.all().order_by('-registro_de_custo__data_custo')


        # --- 5. Histórico de Reprodução (Se existir o modelo) ---
        try:
            context['reproducoes'] = animal.reproducoes.all().order_by('-data_cobertura')
        except:
             context['reproducoes'] = []

        # --- 6. Histórico de Saúde (Se existir o modelo) ---
        try:
             context['tratamentos'] = animal.tratamentos_saude.all().order_by('-data_tratamento')
        except:
             context['tratamentos'] = []

        return context

    def calcular_gpmd(self, pesagens):
        # Apenas tenta calcular se houver pelo menos 2 pesagens
        if pesagens.count() >= 2:
            # Pega as duas últimas pesagens
            pesagem_recente = pesagens.last()
            pesagem_anterior = pesagens[pesagens.count() - 2] 

            peso_recente = pesagem_recente.peso_kg
            data_recente = pesagem_recente.data_pesagem
            
            peso_anterior = pesagem_anterior.peso_kg
            data_anterior = pesagem_anterior.data_pesagem
            
            # Cálculo da Diferença
            diferenca_peso = peso_recente - peso_anterior
            diferenca_dias = (data_recente - data_anterior).days

            # Evita divisão por zero
            if diferenca_dias > 0:
                gpmd = diferenca_peso / diferenca_dias
            else:
                gpmd = None # Não é possível calcular
                
            return {
                'gpmd_dias': diferenca_dias,
                'gpmd_peso_anterior': peso_anterior,
                'gpmd_data_anterior': data_anterior,
                'gpmd_peso_recente': peso_recente,
                'gpmd': round(gpmd * 1000) if gpmd else None # GPMD em gramas
            }
        
        return {
            'gpmd_dias': 0, 
            'gpmd': None,
            'gpmd_peso_recente': pesagens.last().peso_kg if pesagens.count() == 1 else None # Mostra 1ª pesagem
        }


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


class DashboardView(TemplateView):
    template_name = 'pecuaria/dashboard.html'

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
            
                if animal.idade_meses >= meses_desmame_min and animal.idade_meses <= meses_desmame_max:
                    alerta_desmame.append({
                        'identificacao': animal.identificacao,
                        'idade_meses': animal.idade_meses,
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
        total_abatido = Animal.objects.filter(situacao='ABATIDO').count()
        
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
            'total_abatido': total_abatido,
        }
        
        return context


# Define as categorias de idade em meses
# Você pode ajustar estas faixas conforme a sua necessidade zootécnica
IDADE_CATEGORIAS = [
    (12, '0 a 12 Meses (Cria)'),
    (24, '13 a 24 Meses (Recria)'),
    (36, '25 a 36 Meses (Recria Avançada)'),
    (999, 'Acima de 36 Meses (Matrizes/Reprodutores)'),
]

# Limites para a análise detalhada de bezerros (1 a 9 meses)
BEZERRO_LIMITES = list(range(1, 10)) 

class AnalisePorIdadeView(TemplateView):
    template_name = 'pecuaria/analise_por_idade.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        
        # 1. CÁLCULO DA IDADE CORRIGIDO
        # Calcula a diferença de datas (DurationField)
        duration_expr = today - F('data_nascimento')
        
        # Converte a Duration para dias (dividindo pela duração de um dia) e define o resultado como Float
        idade_em_dias_expr = ExpressionWrapper(
            duration_expr / timedelta(days=1),
            output_field=FloatField() # Garante que o resultado é um número (dias)
        )
        
        # Converte dias para meses (dividindo por 30.4 dias/mês)
        idade_em_meses_expr = ExpressionWrapper(
            idade_em_dias_expr / 30.4,
            output_field=IntegerField() # O resultado final que queremos para categorização
        )

        # Filtra animais vivos com data de nascimento válida
        animais_base = Animal.objects.filter(
            situacao='VIVO',
            data_nascimento__isnull=False,
        ).annotate(
            idade_meses=idade_em_meses_expr # Usa a nova expressão corrigida
        )
        
        # --- 2. Análise Detalhada dos Bezerros (0 a 9 meses) ---
        analise_bezerros = []
        limite_anterior = 0

        for limite_meses in BEZERRO_LIMITES:
            
            # Filtra os animais na faixa atual (maior que o limite anterior, menor ou igual ao limite atual)
            animais_na_faixa = animais_base.filter(
                idade_meses__gt=limite_anterior,
                idade_meses__lte=limite_meses
            )
            
            # Conta machos e fêmeas na faixa
            contagem_sexo = animais_na_faixa.aggregate(
                machos=Count(Case(When(sexo='M', then=1), output_field=IntegerField())),
                femeas=Count(Case(When(sexo='F', then=1), output_field=IntegerField())),
                total=Count('id')
            )
            
            # Cria o nome da categoria
            nome_categoria = f'{limite_anterior} a {limite_meses} Meses'
            
            analise_bezerros.append({
                'categoria': nome_categoria,
                'machos': contagem_sexo['machos'],
                'femeas': contagem_sexo['femeas'],
                'total': contagem_sexo['total'],
                'porcentagem': 0 # Será calculado no template
            })
            
            limite_anterior = limite_meses # O novo limite anterior será o limite atual (9 meses)


        # --- 3. Análise Geral (começa após 9 meses) ---
        analise_geral = []
        limite_anterior = 9 # Continua de onde os bezerros pararam

        for limite_meses, nome_categoria in IDADE_CATEGORIAS:
            
            animais_na_faixa = animais_base.filter(
                idade_meses__gt=limite_anterior,
                idade_meses__lte=limite_meses
            )
            
            contagem_sexo = animais_na_faixa.aggregate(
                machos=Count(Case(When(sexo='M', then=1), output_field=IntegerField())),
                femeas=Count(Case(When(sexo='F', then=1), output_field=IntegerField())),
                total=Count('id')
            )
            
            analise_geral.append({
                'categoria': nome_categoria,
                'machos': contagem_sexo['machos'],
                'femeas': contagem_sexo['femeas'],
                'total': contagem_sexo['total'],
                'porcentagem': 0
            })
            
            limite_anterior = limite_meses

        context['analise_bezerros'] = analise_bezerros
        context['analise_geral'] = analise_geral
        context['total_geral'] = animais_base.count() # Total de animais na análise
        
        return context


# --- TRATAMENTO DE SAÚDE ---
class TratamentoSaudeListView(LoginRequiredMixin, ListView):
    model = TratamentoSaude
    template_name = 'pecuaria/tratamentos_saude_list.html'
    context_object_name = 'tratamentos'
    # Ordena os registros pela data do tratamento mais recente
    ordering = ['-data_tratamento']


# ---  MANEJO REPRODUTIVO ---
class ReproducaoListView(LoginRequiredMixin, ListView):
    model = Reproducao
    template_name = 'pecuaria/reproducao_list.html'
    context_object_name = 'manejo_reprodutivo'
    # Ordena os registros pela data do cio mais recente
    ordering = ['-data_cio'] 


class PesagemListView(ListView):
    model = Pesagem
    template_name = 'pecuaria/pesagem_list.html'
    context_object_name = 'pesagens'
    # Ordena os registros pela data mais recente
    ordering = ['-data_pesagem'] 


# Função para calcular o GPMD de um animal (baseado no ciclo de pesagens)
def calcular_gpmd_animal(animal):
    pesagens = animal.pesagem_set.all().order_by('data_pesagem')
    
    if pesagens.count() < 2:
        return None # GPMD não pode ser calculado com menos de 2 pesagens

    primeira = pesagens.first()
    ultima = pesagens.last()

    peso_total_ganho = ultima.peso_kg - primeira.peso_kg
    dias = (ultima.data_pesagem - primeira.data_pesagem).days
    
    if dias > 0:
        return peso_total_ganho / Decimal(dias)
    return None


class AnaliseDesempenhoLotesCBV(TemplateView):
    template_name = 'pecuaria/analise_lotes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Obter todos os lotes (usando Pasto como Lote)
        lotes = Lote.objects.all()
        
        dados_lotes = []
        
        for lote in lotes:
            animais_no_lote = Animal.objects.filter(lote_atual=lote, situacao='VIVO')
            
            gpmds_dos_animais = []
            
            # 2. Calcular o GPMD Médio individualmente (em Python)
            for animal in animais_no_lote:
                gpmd_animal = calcular_gpmd_animal(animal)
                if gpmd_animal is not None:
                    gpmds_dos_animais.append(gpmd_animal)
            
            gpmd_medio = None
            if gpmds_dos_animais:
                gpmd_medio = sum(gpmds_dos_animais) / len(gpmds_dos_animais)
            
            # 3. Reunir os dados
            dados_lotes.append({
                'lote': lote,
                'pasto_atual': lote.nome, 
                'total_animais': animais_no_lote.count(),
                'gpmd_medio': round(gpmd_medio, 2) if gpmd_medio is not None else 'N/A'
            })

        # 4. Ordenação
        dados_lotes.sort(key=lambda x: x['gpmd_medio'] if x['gpmd_medio'] != 'N/A' else -1, reverse=True)

        context.update({
            'dados_lotes': dados_lotes,
        })
        
        return context


@login_required
def analise_idade_sexo_lotes(request):
    lotes_ativos = Lote.objects.filter(animais_no_lote__situacao='VIVO').distinct()
    dados_lotes = []
    today = date.today()

    for lote in lotes_ativos:
        # Filtra apenas animais ativos no lote
        animais = Animal.objects.filter(lote_atual=lote, situacao='VIVO')
        total_animais = animais.count()
        
        # 1. Contagem por sexo
        machos = animais.filter(sexo='M').count()
        femeas = animais.filter(sexo='F').count()
        
        # 2. Cálculo da Idade Média
        total_dias = 0
        if total_animais > 0:
            for animal in animais:
                # Calcula a diferença de dias entre hoje e a data de nascimento
                age_in_days = (today - animal.data_nascimento).days
                total_dias += age_in_days
            
            avg_age_in_days = total_dias / total_animais
            
            # Converte a média de dias para Anos e Meses
            avg_years = int(avg_age_in_days // 365.25)
            remaining_days = avg_age_in_days % 365.25
            avg_months = int(remaining_days // (365.25 / 12))
            
            idade_media_formatada = f"{avg_years}a e {avg_months}m"
        else:
            idade_media_formatada = "N/A"

        # 3. Reúne os dados
        dados_lotes.append({
            'lote': lote,
            'total_animais': total_animais,
            'machos': machos,
            'femeas': femeas,
            'idade_media': idade_media_formatada,
            'pasto_atual': lote.pasto_atual.nome if lote.pasto_atual else 'N/A'
        })

    context = {
        'dados_lotes': dados_lotes,
    }
    
    return render(request, 'pecuaria/analise_idade_sexo_lotes.html', context)