from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Q
from .models import  BaixaAnimal


@receiver(post_save, sender=BaixaAnimal)
def update_animal_situacao_on_baixa(sender, instance, created, **kwargs):
    if created:
        animal = instance.animal
        animal.situacao = 'MORTO'
        animal.save(update_fields=['situacao']) # Altera o status para MORTO
