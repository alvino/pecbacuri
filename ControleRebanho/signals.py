from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from .models import Animal, MovimentacaoPasto, RegistroDeCusto, CustoAnimalDetalhe, Venda, Abate, BaixaAnimal, Despesa, TipoCusto


@receiver(post_save, sender=Despesa)
def sync_despesa_to_registro_de_custo(sender, instance, created, **kwargs):
    
    # Tenta encontrar ou criar o TipoCusto que corresponde à CategoriaDespesa
    tipo_custo_obj, _ = TipoCusto.objects.get_or_create(
        nome=instance.categoria.nome, # Usa o nome da CategoriaDespesa
        defaults={'descricao': f"Gerado automaticamente pela Despesa {instance.categoria.nome}"}
    )
    
    desc_registro = f"[DESP. {instance.categoria.nome}] {instance.descricao}"

    if created or not instance.registro_de_custo:
        # Cria um novo RegistroDeCusto
        registro = RegistroDeCusto.objects.create(
            data_custo=instance.data_pagamento,
            descricao=desc_registro,
            valor=instance.valor,
            tipo_custo=tipo_custo_obj 
        )
        # Linka a Despesa ao novo RegistroDeCusto
        instance.registro_de_custo = registro
        instance.save(update_fields=['registro_de_custo'])

    else:
        # Atualiza o RegistroDeCusto existente
        registro = instance.registro_de_custo
        registro.data_custo = instance.data_pagamento
        registro.descricao = desc_registro
        registro.valor = instance.valor
        registro.tipo_custo = tipo_custo_obj 
        registro.save()


# NOVO SIGNAL CONSOLIDADO

@receiver(post_save, sender=MovimentacaoPasto)
def atualizar_animal_e_fechar_movimentacao_anterior(sender, instance, created, **kwargs):
   # 1. Apenas processa se for uma movimentação em aberto (a atual)
    if instance.data_saida is None:
        animal = instance.animal
        
        # Lógica que só roda na criação de um novo registro:
        if created:

            # 1.2. 🚩 NOVO: FECHA A MOVIMENTAÇÃO ANTERIOR (garantindo que só uma esteja aberta)
            # Filtra todas as movimentações abertas para este animal, exceto a atual
            movimentacao_anterior = MovimentacaoPasto.objects.filter(
                animal=animal,
                data_saida__isnull=True
            ).exclude(pk=instance.pk).first()

            # Se encontrar, feche-a
            if movimentacao_anterior:
                # Usa .update() para evitar disparar este signal novamente
                MovimentacaoPasto.objects.filter(pk=movimentacao_anterior.pk).update(data_saida=instance.data_entrada)
        
        # 2. Atualiza o pasto_atual do Animal (Roda na criação e em updates da movimentação)
        animal.pasto_atual = instance.pasto_destino
        
        # 3. Salva o Animal.
        animal.save(update_fields=['pasto_atual'])


@receiver(post_save, sender=RegistroDeCusto)
def alocar_custo_por_pasto(sender, instance, created, **kwargs):
    # 1. Verifica se o custo se aplica a um pasto
    if instance.pasto and created:
        pasto_destino = instance.pasto
        data_custo = instance.data_custo
        valor_total = instance.valor
        
        # 2. Lógica para encontrar os animais no pasto na data do custo
        # Um animal estava no pasto se:
        # - Ele tem uma movimentação cujo destino é o pasto_destino
        # - A data de entrada na movimentação é <= data_custo
        # - A data de saída é > data_custo OU data_saida é nula (movimentação aberta)
        
        animais_no_pasto = Animal.objects.filter(
            movimentacoes_pasto__pasto_destino=pasto_destino,
            movimentacoes_pasto__data_entrada__lte=data_custo
        ).filter(
            Q(movimentacoes_pasto__data_saida__gt=data_custo) | Q(movimentacoes_pasto__data_saida__isnull=True)
        ).distinct()
        
        quantidade_animais = animais_no_pasto.count()
        
        # Se houver animais, aloca o custo
        if quantidade_animais > 0:
            valor_por_animal = valor_total / quantidade_animais
            
            # Limpa alocações antigas, se houver (para garantir idempotência, embora só deva rodar em 'created')
            CustoAnimalDetalhe.objects.filter(registro_de_custo=instance).delete()
            
            # Cria os detalhes de custo
            detalhes = [
                CustoAnimalDetalhe(
                    registro_de_custo=instance,
                    animal=animal,
                    valor_alocado=valor_por_animal
                ) for animal in animais_no_pasto
            ]
            
            CustoAnimalDetalhe.objects.bulk_create(detalhes)
        
        # Se o custo for individualizado (aplicado a um animal), registra o detalhe também
        elif instance.animal and created:
            CustoAnimalDetalhe.objects.create(
                registro_de_custo=instance,
                animal=instance.animal,
                valor_alocado=instance.valor
            )


@receiver(post_save, sender=Venda)
def update_animal_situacao_on_venda(sender, instance, created, **kwargs):
    if created:
        animal = instance.animal
        animal.situacao = 'VENDIDO'
        animal.save(update_fields=['situacao']) # Otimiza, salvando apenas o campo status


@receiver(post_save, sender=Abate)
def update_animal_situacao_on_abate(sender, instance, created, **kwargs):

    if created:
        animal = instance.animal
        animal.situacao = 'ABATIDO'
        animal.save(update_fields=['situacao']) # Otimiza, salvando apenas o campo status


@receiver(post_save, sender=BaixaAnimal)
def update_animal_situacao_on_baixa(sender, instance, created, **kwargs):
    if created:
        animal = instance.animal
        animal.situacao = 'MORTO'
        animal.save(update_fields=['situacao']) # Altera o status para MORTO
