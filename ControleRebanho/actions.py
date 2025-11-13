from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import render, redirect

from .models import Animal, MovimentacaoPasto
from .forms import MudarPastoForm, MudarLoteAnimalForm


@admin.action(description='Mudar animais selecionados para outro Lote')
def mudar_lote_animal(modeladmin, request, queryset):
    # Lida com o POST do formulário
    if 'apply' in request.POST:
        form = MudarLoteAnimalForm(request.POST)
        
        if form.is_valid():
            lote_destino = form.cleaned_data['lote_destino']
            data_entrada = form.cleaned_data['data_entrada']
            observacoes = form.cleaned_data['observacoes']

            # Obtém o pasto do lote de destino (pode ser None)
            pasto_destino = lote_destino.pasto_atual
            
            try:
                with transaction.atomic():
                    movimentados_count = 0
                    
                    for animal in queryset:
                        
                        lote_origem = animal.lote_atual
                        pasto_origem = animal.pasto_atual
                        
                        # Campos que serão atualizados no Animal
                        update_fields = ['lote_atual']

                        # 1. ATUALIZAÇÃO DO LOTE
                        animal.lote_atual = lote_destino
                        
                        # 2. ATUALIZAÇÃO DO PASTO (Regra de Negócio Solicitada)
                        # Apenas move o animal se o lote de destino tiver um pasto.
                        if pasto_destino and pasto_destino != pasto_origem:
                            
                            animal.pasto_atual = pasto_destino
                            update_fields.append('pasto_atual')
                            
                            # 3. CRIAÇÃO DO REGISTRO DE MOVIMENTAÇÃO DE PASTO
                            MovimentacaoPasto.objects.create(
                                animal=animal,
                                pasto_origem=pasto_origem,
                                pasto_destino=pasto_destino,
                                data_entrada=data_entrada,
                                motivo=f"Movimentação via Lote {lote_destino.nome}: {observacoes}"
                            )
                        
                        # Salva o Animal com as atualizações (lote e pasto, se aplicável)
                        animal.save(update_fields=update_fields)
                        
                        movimentados_count += 1
                
                # Mensagem de sucesso
                modeladmin.message_user(
                    request,
                    f"{movimentados_count} animal(is) agora pertencem ao lote '{lote_destino.nome}'.",
                    messages.SUCCESS
                )

            except Exception as e:
                # Mensagem de erro
                modeladmin.message_user(
                    request,
                    f"Erro ao mudar o lote dos animais: {e}",
                    messages.ERROR
                )

            # Redireciona de volta para a changelist do Animal
            return redirect('admin:%s_%s_changelist' % (modeladmin.model._meta.app_label, modeladmin.model._meta.model_name))
            
    # Lida com o GET (renderização inicial)
    else:
        form = MudarLoteAnimalForm()

    # --- Contexto para Renderização do Template ---
    context = {
        'opts': modeladmin.model._meta, 
        'queryset': queryset,
        'action_form': form,
        'title': "Mudar Lote dos Animais",
        'media': modeladmin.media,
        'action_name': 'mudar_lote_animal', 
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }

    # Você pode reutilizar o template 'admin/movimentar_lote_action.html'
    # ou criar um novo chamado 'admin/mudar_lote_animal_action.html'.
    # Usaremos um genérico.
    return render(
        request, 
        'admin/movimentar_lote_action.html', # Reutilizando o template de confirmação
        context=context
    )


@admin.action(description='Mudar Pasto dos Lotes Selecionados')
def mudar_pasto_lote(modeladmin, request, queryset_lotes): # O queryset agora é de Lotes
    
    if 'apply' in request.POST:
        form = MudarPastoForm(request.POST)
        
        if form.is_valid():
            pasto_destino = form.cleaned_data['pasto_destino']
            data_entrada = form.cleaned_data['data_entrada'] 
            observacoes = form.cleaned_data['observacoes']
            
            Lote.ob
            try:
                with transaction.atomic():
                    total_animais_movimentados = 0
                    
                    # 1. Itera sobre os Lotes selecionados
                    for lote in queryset_lotes:

                        # --- A. ATUALIZAÇÃO DO PRÓPRIO LOTE ---
                        # Assumimos que o campo no Lote é 'pasto_atual'
                        lote.pasto_atual = pasto_destino
                        lote.save(update_fields=['pasto_atual'])

                        # 2. Encontra TODOS os animais NESTES lotes (usando lote_atual)
                        animais_do_lote = Animal.objects.filter(lote_atual=lote)
                        
                        # Se não houver animais, pule para o próximo lote
                        if not animais_do_lote.exists():
                            continue

                        # 3. Executa a movimentação para cada animal
                        for animal in animais_do_lote:
                            pasto_origem = animal.pasto_atual

                            # Cria o registro de MovimentacaoPasto
                            MovimentacaoPasto.objects.create(
                                animal=animal,
                                pasto_origem=pasto_origem,      
                                pasto_destino=pasto_destino,  
                                data_entrada=data_entrada,   
                                motivo=f"Movimentação de Pasto: {observacoes}"
                            )
                            
                            # Atualiza o campo pasto_atual do Animal
                            animal.pasto_atual = pasto_destino
                            animal.save(update_fields=['pasto_atual'])
                            
                            total_animais_movimentados += 1
                
                # Mensagem de sucesso
                messages.success(
                    request,
                    f"{total_animais_movimentados} animal(is) de {queryset_lotes.count()} lote(s) movimentado(s) para o pasto '{pasto_destino.nome}'.",
                )
                
            except Exception as e:
                messages.error(
                    request,
                    f"Erro ao movimentar os lotes: {e}",
                )

            # Redireciona de volta para a changelist de Lotes
            return redirect('admin:%s_%s_changelist' % (modeladmin.model._meta.app_label, modeladmin.model._meta.model_name))
            
    # Lida com GET (renderização inicial)
    else:
        form = MudarPastoForm()

    context = {
        'opts': modeladmin.model._meta,
        'queryset_lotes': queryset_lotes, # Passa o queryset de Lotes
        'action_form': form,
        'title': f"Mudar Pasto de {queryset_lotes.count()} Lote(s)",
        'media': modeladmin.media,
        'action_name': 'mudar_pasto_lote',
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }

    # Você precisará criar este template, baseado no anterior!
    return render(
        request, 
        'admin/mudar_pasto_lote_action.html', 
        context=context
    )



@admin.action(description='Mover animais para novo Pasto')
def movimentar_animais(modeladmin, request, queryset):
    
    if 'apply' in request.POST:
        form = MudarPastoForm(request.POST)
        if form.is_valid():
            pasto_destino = form.cleaned_data['pasto_destino']
            data_entrada = form.cleaned_data['data_entrada']
            observacoes = form.cleaned_data['observacoes']
            try:
                with transaction.atomic():
                    movimentados_count = 0

                    for animal in queryset:
                        pasto_origem = animal.pasto_atual
                        
                        MovimentacaoPasto.objects.create(
                            animal=animal,
                            pasto_origem=pasto_origem,
                            pasto_destino=pasto_destino,
                            data_entrada=data_entrada,
                            motivo=observacoes
                        )

                        animal.pasto_atual = pasto_destino
                        animal.save(update_fields=['pasto_atual'])

                        movimentados_count += 1


                    modeladmin.message_user(
                        request,
                        f"{movimentados_count} animal(is) movimentado(s) com sucesso para o pasto '{pasto_destino.nome}'.",
                        messages.SUCCESS
                    )
            except Exception as e:
                # Mensagem de erro
                modeladmin.message_user(
                    request,
                    f"Erro ao movimentar os animais: {e}",
                    messages.ERROR
                )
            return redirect('admin:%s_%s_changelist' % (modeladmin.model._meta.app_label, modeladmin.model._meta.model_name))
    
    else:
        # Se for o GET, inicializa o formulário vazio
        form = MudarPastoForm()

    # --- Contexto para Renderização do Template ---
    context = {
        'opts': modeladmin.model._meta, 
        'queryset': queryset,
        'action_form': form,
        'title': "Movimentar Animais",
        'media': modeladmin.media,
        'action_name': 'movimentar_animais', 
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
    }

    # Renderiza o template
    return render(
        request, 
        'admin/mudar_pasto_animal_action.html', 
        context=context
    )