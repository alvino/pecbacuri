from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from .models import Animal, MovimentacaoPasto, RegistroDeCusto, CustoAnimalDetalhe, Venda, Abate, BaixaAnimal, Despesa, Lote


@receiver(post_save, sender=Despesa)
def sync_despesa_to_registro_de_custo(sender, instance, created, **kwargs):
    """Cria ou atualiza um RegistroDeCusto quando uma Despesa é salva."""
    
    # Prepara a descrição para o RegistroDeCusto
    desc_registro = f"[DESP. {instance.categoria.nome}] {instance.descricao}"

    if created or not instance.registro_de_custo:
        # Cria um novo RegistroDeCusto
        registro = RegistroDeCusto.objects.create(
            data_custo=instance.data_pagamento,
            descricao=desc_registro,
            valor=instance.valor,
            categoria=instance.categoria.nome # Mantém a categoria para fins de compatibilidade
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
        registro.categoria = instance.categoria.nome
        registro.save()


@receiver(post_save, sender=MovimentacaoPasto)
def atualizar_pasto_animal(sender, instance, created, **kwargs):
    """
    Atualiza o campo pasto_atual do animal sempre que uma nova
    MovimentacaoPasto for criada.
    """
    
    # Se a movimentação tem data_saida em branco, significa que é a movimentação atual.
    if instance.data_saida is None:
        animal = instance.animal
        
        # 1. Atualiza o pasto_atual do Animal
        animal.pasto_atual = instance.pasto_destino
        
        # 2. Salva o Animal. Usamos update_fields para evitar loops de signal.
        animal.save(update_fields=['pasto_atual'])


@receiver(post_save, sender=MovimentacaoPasto)
def update_animal_pasto_on_movimentacao(sender, instance, created, **kwargs):
    """
    Atualiza o campo 'pasto' do animal para o 'pasto_destino' da movimentação,
    e preenche o pasto_origem se estiver vazio.
    """
    if created:
        animal = instance.animal
        
        # 1. Preenche o pasto de origem automaticamente (Se vier do admin e estiver vazio)
        if not instance.pasto_origem:
            instance.pasto_origem = animal.pasto_atual
            # Salva a instância novamente (apenas o campo de origem)
            MovimentacaoPasto.objects.filter(pk=instance.pk).update(pasto_origem=animal.pasto_atual)

        lote_atual = Lote.objects.filter(pasto_atual=animal.pasto_atual)
        if lote_atual.acount == 1:
            animal.lote_atual = lote_atual
        # 2. Atualiza a localização atual do Animal
        animal.pasto_atual = instance.pasto_destino 
        animal.save(update_fields=['pasto_atual'])


@receiver(post_save, sender=RegistroDeCusto)
def alocar_custo_por_pasto(sender, instance, created, **kwargs):

    """
    Executa a alocação de custos por pasto para os animais que 
    estavam nele na data do registro.
    """
    
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
def update_animal_status_on_venda(sender, instance, created, **kwargs):
    if created:
        animal = instance.animal
        animal.status = 'VENDIDO'
        animal.save(update_fields=['status']) # Otimiza, salvando apenas o campo status


@receiver(post_save, sender=Abate)
def update_animal_status_on_abate(sender, instance, created, **kwargs):

    if created:
        animal = instance.animal
        animal.status = 'ABATIDO'
        animal.save(update_fields=['status']) # Otimiza, salvando apenas o campo status


@receiver(post_save, sender=BaixaAnimal)
def update_animal_situacao_on_baixa(sender, instance, created, **kwargs):
    if created:
        animal = instance.animal
        animal.situacao = 'MORTO'
        animal.save(update_fields=['situacao']) # Altera o status para MORTO
