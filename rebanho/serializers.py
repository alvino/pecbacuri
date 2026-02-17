# ControleRebanho/serializers.py

from rest_framework import serializers
from .models import Animal

class AnimalSerializer(serializers.ModelSerializer):
    # Campo para mostrar o nome do pasto em vez do ID
    pasto_nome = serializers.ReadOnlyField(source='pasto_atual.nome')
    lote_nome = serializers.ReadOnlyField(source='lote_atual.nome')
    
    class Meta:
        model = Animal
        fields = (
            'id',
            'identificacao',
            'nome',
            'data_nascimento',
            'sexo',
            'situacao',
            'observacoes',
            'mae',
            'pai',
            'lote_atual',
            'lote_nome',
            'pasto_atual',
            'pasto_nome',
        )
        # Excluir o campo 'pasto' se você só quiser o nome
        # fields = '__all__' # para incluir todos os campos (não recomendado em produção)