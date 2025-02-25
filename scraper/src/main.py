#!/usr/bin/env python3
import argparse
import logging
from .scraper import CariocaDigitalScraper

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")


def main():
    # Configurar argumentos da linha de comando
    parser = argparse.ArgumentParser(
        description="Scraper para o portal Carioca Digital"
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 0],
        default=0,
        help="Etapa a executar: 1 (extrair links), 2 (scraping dos links), 0 (ambas etapas)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data",
        help="Diretório para salvar os dados extraídos",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="https://home.carioca.rio/",
        help="URL base para iniciar o scraping",
    )

    args = parser.parse_args()

    # Inicializar o scraper
    scraper = CariocaDigitalScraper(base_url=args.base_url, output_dir=args.output_dir)

    # Executar a etapa solicitada
    if args.step == 1 or args.step == 0:
        print("Etapa 1: Extraindo links mais buscados...")
        scraper.extract_most_searched_links()
        print("Etapa 1 concluída!")

    if args.step == 2 or args.step == 0:
        print("Etapa 2: Fazendo scraping dos links mais buscados...")
        scraper.scrape_most_searched_links()
        print("Etapa 2 concluída!")

    print("Processo finalizado com sucesso!")


if __name__ == "__main__":
    main()
