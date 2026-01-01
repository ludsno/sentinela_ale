\
# Sentinela AL

Dashboard em Streamlit + coletor (ingestor) para acompanhar a evolução da folha de pagamento publicada no portal de transparência da Assembleia Legislativa de Alagoas (ALE-AL).

## Acesso rápido

- App (Streamlit): https://sentinelaale-qvhg6krqhien5uhl3mw8ux.streamlit.app/

Este repositório é um projeto de portfólio voltado a **Engenharia de Dados** (coleta, armazenamento, transformação) e **Visualização** (indicadores e gráficos).

## Aviso legal

- Os dados são obtidos a partir de uma **fonte pública** (portal de transparência).
- Podem ocorrer erros de extração/parsing e inconsistências na fonte.
- Não tire conclusões sem conferir na fonte oficial.
- O projeto **não possui vínculo oficial** com a ALE-AL ou órgãos de controle.

## O que o projeto faz

- Coleta mensal de registros no portal (por ano/mês), acessando as páginas de detalhamento.
- Normaliza valores monetários e armazena o histórico em SQLite (por padrão).
- Exibe um dashboard com:
	- Evolução de custo e quantidade de pessoas.
	- Rotatividade (admissões/saídas entre competências).
	- Progressões/anomalias de remuneração.
	- Rankings e análise individual.

## Imagens

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/fb718d79-4b2f-4505-a932-6bdcc10e89ed" />
---
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/e6b50179-2d19-4134-b678-991dec11d177" />


## Stack

- Python 3
- Streamlit (UI)
- Pandas (ETL)
- SQLAlchemy + SQLite (persistência)
- Requests + BeautifulSoup (scraping)
- Plotly (gráficos)

## Estrutura do repositório

- app_k11.py: dashboard Streamlit
- ingestor_turbo.py: coletor com paralelismo (ThreadPool)
- models.py: schema e conexão com o banco
- requirements.txt: dependências
- .github/workflows/atualização_mensal.yml: automação (se configurado)

## Requisitos

- Python 3.10+ (recomendado)
- Conexão com a internet para a coleta

## Instalação

No Windows (PowerShell), dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuração

### Banco de dados

Por padrão o projeto usa SQLite local em:

- sentinela_alagoas.db

Você pode trocar o destino via variável de ambiente:

- DATABASE_URL

Exemplo (SQLite em caminho customizado):

```powershell
$env:DATABASE_URL = "sqlite:///c:/temp/sentinela_alagoas.db"
```

### Modo de carga

O ingestor possui dois modos:

- Manutenção mensal (padrão): varre apenas o ano atual.
- Carga histórica: varre de 2020 até o ano atual.

Ative a carga histórica com:

```powershell
$env:CARGA_HISTORICA = "true"
```

## Como usar

### 1) Popular/atualizar o banco

Rode o ingestor:

```powershell
python ingestor_turbo.py
```

Isso irá:

- Garantir que o banco e a tabela existam.
- Baixar competências (ano/mês) e inserir novos registros.

Observações:

- O ingestor faz paralelismo (várias requisições simultâneas). Se o portal limitar/bloquear, reduza o número de workers em ingestor_turbo.py.
- Se o portal estiver fora do ar, a coleta pode falhar.

### 2) Abrir o dashboard

App público (Streamlit): https://sentinelaale-qvhg6krqhien5uhl3mw8ux.streamlit.app/

Com o banco preenchido:

```powershell
streamlit run app_k11.py
```

Se aparecer a mensagem de “banco vazio”, execute primeiro o ingestor.

## Automação (GitHub Actions)

O workflow .github/workflows/atualização_mensal.yml pode ser usado para rodar a atualização automaticamente.

Para funcionar em CI você precisa garantir:

- Python instalado no runner.
- Dependências instaladas (requirements.txt).
- Estratégia para persistir o banco (ex.: artifact, storage, ou database externo via DATABASE_URL).

## Troubleshooting

### Erro: “Banco de dados vazio” no dashboard

- Rode: python ingestor_turbo.py

### Erros de parsing (pandas.read_html)

- O layout do portal pode ter mudado. Ajuste o seletor/match em ingestor_turbo.py.

### SQLite e concorrência

- O SQLite é suficiente para uso local. Para múltiplas execuções concorrentes/CI, considere um banco externo via DATABASE_URL.

## Licença

Uso livre para fins educacionais e de portfólio. Se você pretende reutilizar em contexto público/comercial, revise o uso de dados e as regras do portal de origem.


