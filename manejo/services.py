from django.db.models import Q
from .models import Reproducao

class ReproducaoService:
    @staticmethod
    def obter_dados_estacao(ano_inicio):
        """
        Filtra reproduções da Estação de Monta (Outubro/Ano a Março/Ano+1)
        """
        ano_fim = int(ano_inicio) + 1
        
        # Filtro complexo: 
        # (Ano início E meses >= 10) OU (Ano fim E meses <= 3)
        filtro_estacao = Q(data_cio__year=ano_inicio, data_cio__month__gte=10) | \
                         Q(data_cio__year=ano_fim, data_cio__month__lte=3)
        
        reproducoes = Reproducao.objects.filter(filtro_estacao)
        
        total_servicos = reproducoes.count()

        prenhezes = reproducoes.filter(resultado='P').count() or 0
        
        vazias = reproducoes.filter(resultado='V').count() or 0

        nao_verificadas = reproducoes.filter(resultado='N').count() or 0

        # Taxa de Prenhez da Estação
        taxa_prenhez = (prenhezes / total_servicos * 100) if total_servicos > 0 else 0
        
        return {
            'reproducoes': reproducoes,
            'total_servicos': total_servicos,
            'prenhezes': prenhezes,
            'vazias': vazias,
            'nao_verificadas': nao_verificadas,
            'taxa_prenhez': round(taxa_prenhez, 1),
            'nome_estacao': f"{ano_inicio}/{ano_fim}"
        }