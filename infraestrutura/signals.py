from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from .models import  MovimentacaoPasto


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


