# 🐂 PECBACURI - Sistema de Gestão Pecuária

[![Status do Projeto](https://img.shields.io/badge/Status-Em%20Desenvolvimento-blue)](https://github.com/alvino/pecbacuri.git)
[![Tecnologia Principal](https://img.shields.io/badge/Backend-Django%20(Python)-green)](https://www.djangoproject.com/)
[![API Status](https://img.shields.io/badge/API-REST%20(DRF)-orange)](https://www.django-rest-framework.org/)

## 📝 Descrição do Projeto

O **PECBACURI** é um sistema robusto de controle zootécnico e financeiro, desenvolvido para otimizar a gestão de fazendas de corte e leite. O projeto utiliza o framework Django para garantir segurança, agilidade e um ORM eficiente.

O principal objetivo é fornecer ao pecuarista indicadores críticos de desempenho (*KPIs*) e alertas de risco para suportar a tomada de decisão, maximizando a produtividade e a lucratividade do rebanho.

---

## ✨ Funcionalidades Principais

### Módulo de Controle Zootécnico
* **Gestão de Inventário:** Cadastro e controle individual de animais (matrizes, reprodutores, bezerros).
* **Histórico de Pesagens:** Registro e análise da evolução de peso para cálculo do **Ganho Médio Diário de Peso (GPMD)**.
* **Controle de Lotes e Pastos:** Associação de animais a lotes e pastos, permitindo análise de desempenho por grupo.
* **Controle de Sanidade (Próxima Fase):** Preparado para registrar vacinas, medicamentos e tratamentos.

### Módulo Financeiro e de Custos
* **Registro de Custos:** Entrada de despesas operacionais (ração, insumos, mão-de-obra, etc.).
* **Alocação de Custo:** Distribuição inteligente dos custos para o nível do animal/lote, permitindo o cálculo do **Custo da Mercadoria Vendida (CMV)**.
* **Vendas e Abates:** Registro de saídas do rebanho com cálculo de margem de lucro por animal/lote.

### Dashboards e Análise (CBVs e Alertas)
* **Dashboard Financeiro:** Visão consolidada de receitas, despesas e margens operacionais.
* **Análise de Desempenho:** Visualização de KPIs zootécnicos por lote.
* **Alertas Preditivos de Risco:** Sistema que sinaliza automaticamente animais com **GPMD baixo**, **custo acumulado alto** ou **falta de pesagem** recente.

### API REST
* O Backend está exposto via **Django REST Framework (DRF)**, permitindo que a lógica de negócio e os dados sejam consumidos por interfaces modernas (como um aplicativo móvel ou desktop via Electron.js).

---

## 🚀 Como Executar o Projeto Localmente

Siga estas instruções para configurar o ambiente de desenvolvimento.

### Pré-requisitos
* [Python 3.10+](https://www.python.org/downloads/)
* [pip] (Gerenciador de pacotes Python)

### 1. Clonar o Repositório

```bash
git clone https://github.com/alvino/pecbacuri.git
cd pecbacuri
```

### 2. Configurar o Ambiente Virtual

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows use: venv\Scripts\activate
```

### 3. Instalar Dependências

Instale todos os pacotes necessários, incluindo Django e DRF:

```bash
pip install -r requirements.txt  # Se você tiver um requirements.txt
```
#### Se não tiver, use:
#### pip install django djangorestframework python-decouple psycopg2-binary

### 4. Configurar o Banco de Dados e Migrações

O projeto usa SQLite por padrão para desenvolvimento (pode ser alterado no settings.py).
Bash
```bash
python manage.py makemigrations ControleRebanho
python manage.py migrate
```

### 5. Criar um Superusuário

Necessário para acessar o Django Admin e carregar dados iniciais.
```bash
python manage.py createsuperuser
```

### 6. Iniciar o Servidor


```bash
python manage.py runserver
```

O projeto estará acessível em: [http://127.0.0.1:8000/](http://127.0.0.1:8000/) O Painel de Administração estará em: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

A API REST base está em: [http://127.0.0.1:8000/api/v1/](http://127.0.0.1:8000/api/v1/)