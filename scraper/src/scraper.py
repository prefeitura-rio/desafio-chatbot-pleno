import os
import requests
from bs4 import BeautifulSoup
import json
import logging
import time
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scraper")


class CariocaDigitalScraper:
    def __init__(
        self, base_url: str = "https://home.carioca.rio/", output_dir: str = "./data"
    ):
        self.base_url: str = base_url
        self.output_dir: str = output_dir
        self.visited_urls: Set[str] = set()
        self.data: List[Dict] = []
        self.most_searched_links: List[Dict] = []

        # Criar diretório de saída se não existir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def is_valid_url(self, url: str) -> bool:
        """Verifica se a URL pertence ao domínio carioca.rio e não é um recurso estático"""
        parsed_url = urlparse(url)

        # Verificar se é do domínio carioca.rio
        if "carioca.rio" not in parsed_url.netloc:
            return False

        # Ignorar arquivos estáticos comuns
        ignored_extensions = [
            ".css",
            ".js",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".svg",
            ".ico",
        ]
        if any(parsed_url.path.endswith(ext) for ext in ignored_extensions):
            return False

        return True

    def extract_most_searched_links(self) -> None:
        """
        Extrai links das listas com classe 'ListaMenuMaisBuscados' e salva no disco
        """
        logger.info(f"Extraindo links mais buscados de {self.base_url}")

        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Encontrar todas as listas com a classe ListaMenuMaisBuscados
            most_searched_lists = soup.find_all("ul", class_="ListaMenuMaisBuscados")

            if not most_searched_lists:
                logger.warning("Nenhuma lista 'ListaMenuMaisBuscados' encontrada")
                return

            logger.info(
                f"Encontradas {len(most_searched_lists)} listas de links mais buscados"
            )

            # Para cada lista, extrair os links
            for ul in most_searched_lists:
                # Encontrar o título da categoria (está em um h2 com classe TitleMenuMaisBuscados)
                category_title_elem = ul.find_previous(
                    "h2", class_="TitleMenuMaisBuscados"
                )
                category_title = (
                    category_title_elem.text if category_title_elem else "Sem categoria"
                )

                # Extrair links dentro da lista
                links = ul.find_all("a")

                for link in links:
                    href = link.get("href")
                    if href:
                        absolute_url = urljoin(self.base_url, href)
                        if self.is_valid_url(absolute_url):
                            # Extrair o texto do link (está dentro de um li)
                            link_text = link.find("li")
                            text = link_text.text if link_text else link.text

                            self.most_searched_links.append(
                                {
                                    "url": absolute_url,
                                    "text": text.strip(),
                                    "category": category_title,
                                }
                            )

            logger.info(
                f"Extraídos {len(self.most_searched_links)} links mais buscados"
            )

            # Salvar links no disco
            self.save_most_searched_links()

        except Exception as e:
            logger.error(f"Erro ao extrair links mais buscados: {str(e)}")

    def save_most_searched_links(self) -> None:
        """Salva os links mais buscados em um arquivo JSON"""
        output_file = os.path.join(self.output_dir, "most_searched_links.json")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.most_searched_links, f, ensure_ascii=False, indent=2)

        # Salvar também em formato de texto para fácil visualização
        txt_file = os.path.join(self.output_dir, "most_searched_links.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            for item in self.most_searched_links:
                f.write(f"Categoria: {item['category']}\n")
                f.write(f"Texto: {item['text']}\n")
                f.write(f"URL: {item['url']}\n")
                f.write("-" * 50 + "\n")

        logger.info(f"Links mais buscados salvos em {output_file} e {txt_file}")

    def load_most_searched_links(self) -> List[Dict]:
        """Carrega os links mais buscados do arquivo JSON"""
        input_file = os.path.join(self.output_dir, "most_searched_links.json")

        if not os.path.exists(input_file):
            logger.error(f"Arquivo {input_file} não encontrado")
            return []

        with open(input_file, "r", encoding="utf-8") as f:
            links = json.load(f)

        logger.info(f"Carregados {len(links)} links mais buscados de {input_file}")
        return links

    def extract_content(self, soup: BeautifulSoup, url: str) -> dict:
        """Extrai o conteúdo relevante da página"""
        # Título da página
        title = soup.title.text.strip() if soup.title else "Sem título"

        # Conteúdo principal - extrair apenas das divs com classe "Anchors" que não estão ocultas
        main_content = ""
        html_content = ""

        # Encontrar todas as divs com classe "Anchors"
        anchors_divs = soup.find_all("div", class_="Anchors")

        # Filtrar para remover a div de navegação (que geralmente tem style="display: none;")
        content_divs = []
        for div in anchors_divs:
            # Ignorar divs com style="display: none;"
            style = div.get("style", "")
            if "display: none" not in style:
                content_divs.append(div)

        if content_divs:
            logger.info(
                f"Encontradas {len(content_divs)} divs com classe 'Anchors' relevantes em {url}"
            )

            # Processar cada div relevante
            for div in content_divs:
                # Encontrar o título associado a esta seção, se existir
                section_title = ""
                # Procurar por um botão ou título próximo
                button = div.find("button", class_="btn-link")
                if button:
                    section_title = button.text.strip()

                # Remover scripts e estilos para o texto
                for script in div(["script", "style"]):
                    script.decompose()

                # Extrair o texto
                div_text = div.get_text(separator=" ", strip=True)
                if div_text:
                    if section_title:
                        main_content += f"## {section_title}\n\n{div_text}\n\n"
                    else:
                        main_content += div_text + "\n\n"

                # Salvar também o HTML
                html_content += str(div) + "\n\n"
        else:
            logger.warning(
                f"Nenhuma div com classe 'Anchors' relevante encontrada em {url}"
            )

            # Fallback para o conteúdo principal se não encontrar divs "Anchors" relevantes
            content_selectors = [
                "main",
                "article",
                ".content",
                "#content",
                ".main-content",
                "#main-content",
            ]

            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    # Remover scripts e estilos
                    for script in content_element(["script", "style"]):
                        script.decompose()
                    main_content = content_element.get_text(separator=" ", strip=True)
                    html_content = str(content_element)
                    logger.info(f"Usando seletor fallback '{selector}' para {url}")
                    break

            # Se não encontrou conteúdo com os seletores, pegar o body
            if not main_content:
                body = soup.body
                if body:
                    for script in body(["script", "style"]):
                        script.decompose()
                    main_content = body.get_text(separator=" ", strip=True)
                    html_content = str(body)
                    logger.info(f"Usando body como fallback para {url}")

        # Criar documento estruturado
        document = {
            "url": url,
            "title": title,
            "content": main_content.strip(),
            "html_content": html_content.strip(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        return document

    def extract_links(self, soup: BeautifulSoup, current_url: str) -> list[str]:
        """Extrai links da página para continuar o crawling"""
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(current_url, href)

            # Verificar se é uma URL válida e não foi visitada
            if (
                self.is_valid_url(absolute_url)
                and absolute_url not in self.visited_urls
            ):
                links.append(absolute_url)

        return links

    def scrape_page(self, url: str) -> list[str]:
        """Faz o scraping de uma página específica"""
        if url in self.visited_urls:
            return []

        self.visited_urls.add(url)
        logger.info(f"Scraping: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extrair conteúdo
            document = self.extract_content(soup, url)
            self.data.append(document)

            # Extrair links para continuar o crawling
            links = self.extract_links(soup, url)

            return links

        except Exception as e:
            logger.error(f"Erro ao fazer scraping de {url}: {str(e)}")
            return []

    def scrape_most_searched_links(self) -> None:
        """
        Etapa 2: Faz o scraping das páginas dos links mais buscados
        """
        # Carregar links salvos anteriormente
        links = self.load_most_searched_links()

        if not links:
            logger.error("Nenhum link mais buscado encontrado para fazer scraping")
            return

        logger.info(f"Iniciando scraping de {len(links)} links mais buscados")

        for i, link_info in enumerate(links):
            url = link_info["url"]
            logger.info(f"Scraping link mais buscado ({i+1}/{len(links)}): {url}")

            self.scrape_page(url)

            # Pequena pausa para não sobrecarregar o servidor
            time.sleep(1)

        logger.info(
            f"Scraping de links mais buscados concluído. Total: {len(self.data)} páginas"
        )

        # Salvar os dados coletados
        self.save_data()

    def save_data(self) -> None:
        """Salva os dados coletados em um arquivo JSON"""
        output_file = os.path.join(self.output_dir, "carioca_digital_data.json")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

        logger.info(f"Dados salvos em {output_file}")

        # Salvar também URLs visitadas para referência
        urls_file = os.path.join(self.output_dir, "visited_urls.txt")
        with open(urls_file, "w", encoding="utf-8") as f:
            for url in self.visited_urls:
                f.write(f"{url}\n")

        logger.info(f"URLs visitadas salvas em {urls_file}")
