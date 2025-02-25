# Carioca Digital Scraper

Este scraper foi desenvolvido para extrair informações do portal Carioca Digital (https://home.carioca.rio/) em duas etapas:

1. **Etapa 1**: Extração dos links mais buscados (ListaMenuMaisBuscados)
2. **Etapa 2**: Scraping do conteúdo das páginas dos links extraídos, focando apenas nas divs com classe "Anchors" que contêm o conteúdo principal

## Requisitos

- Python 3.7+
- Bibliotecas listadas em `requirements.txt`

## Instalação

```bash
# Clonar o repositório (se aplicável)
# git clone <url-do-repositorio>
# cd <nome-do-repositorio>

# Criar e ativar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
# venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Uso

O scraper pode ser executado em três modos:

### Modo 1: Apenas extrair links mais buscados

```bash
python run.py --step 1
```

### Modo 2: Apenas fazer scraping dos links já extraídos

```bash
python run.py --step 2
```

### Modo 0 (padrão): Executar ambas as etapas sequencialmente

```bash
python run.py
# ou
python run.py --step 0
```

### Opções adicionais

- `--output-dir`: Diretório para salvar os dados extraídos (padrão: `./data`)
- `--base-url`: URL base para iniciar o scraping (padrão: `https://home.carioca.rio/`)

Exemplo:
```bash
python run.py --output-dir ./meus_dados --base-url https://home.carioca.rio/
```

## Saída

Os dados extraídos são salvos no diretório especificado (padrão: `./data`):

- `most_searched_links.json`: Links mais buscados em formato JSON
- `most_searched_links.txt`: Links mais buscados em formato de texto para fácil visualização
- `carioca_digital_data.json`: Conteúdo extraído das páginas, contendo:
  - `url`: URL da página
  - `title`: Título da página
  - `content`: Conteúdo textual extraído das divs com classe "Anchors" (excluindo as ocultas)
  - `html_content`: Conteúdo HTML das divs com classe "Anchors" (excluindo as ocultas)
  - `timestamp`: Data e hora da extração
- `visited_urls.txt`: Lista de URLs visitadas

## Detalhes da Implementação

- O scraper ignora a primeira div com classe "Anchors" que geralmente contém apenas o menu de navegação (com style="display: none;")
- Apenas as divs com classe "Anchors" que estão visíveis são extraídas
- O conteúdo é organizado com os títulos das seções, quando disponíveis
- Tanto o texto quanto o HTML são salvos para cada página

## Estrutura do Projeto

```
scraper/
├── README.md
├── requirements.txt
├── run.py
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── scraper.py
└── data/
    ├── most_searched_links.json
    ├── most_searched_links.txt
    ├── carioca_digital_data.json
    └── visited_urls.txt
``` 