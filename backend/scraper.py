import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from urllib.parse import urlparse, unquote
import zipfile
import tempfile

class Scraper:
    def __init__(self):
        """
        Initialiseert de Scraper met de basis mapstructuur.
        """
        # Maak de basis download directory aan voor de zip files
        self.base_download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'downloads')
        os.makedirs(self.base_download_dir, exist_ok=True)
        
        # Selenium configuratie
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def fetch_html(self, url):
        """
        Haalt HTML content op met Selenium voor JavaScript-gerenderde content.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"HTML ophalen (poging {attempt + 1}/{max_retries})")
                self.driver.get(url)
                time.sleep(2)  # Geef JavaScript tijd om te laden
                
                try:
                    self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, ".print-document, .document-hoofd"
                    )))
                except Exception as e:
                    print(f"Waarschuwing: Timeout bij wachten op hoofdcontent: {e}")
                
                return self.driver.page_source
                
            except Exception as e:
                print(f"Fout bij ophalen HTML (poging {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)
        return None

    def generate_metadata(self, html_content):
        """
        Genereert metadata van de HTML content.
        
        Parameters:
            html_content (str): HTML content van de webpagina
            
        Returns:
            dict: Dictionary met metadata
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Haal de titel op
            title_div = soup.find('div', class_='print-document')
            title = title_div.find('div', class_='document-hoofd').find('a').get_text(strip=True)

            # Haal de samenvatting op
            summary_td = soup.find('td', class_='zoekoverzicht', colspan="2")
            summary = summary_td.find_all('p')[1].get_text(strip=True) if len(summary_td.find_all('p')) > 1 else ""

            # Haal het creatie jaar op
            creation_year_tag = soup.find('td', string='Creatie jaar')
            creation_year = creation_year_tag.find_next_sibling('td').get_text(strip=True) if creation_year_tag else None

            # Haal de WOO thema's op
            woo_themes_tag = soup.find('td', string="WOO thema's")
            woo_themes_list = woo_themes_tag.find_next_sibling('td').find_all('li') if woo_themes_tag else []
            woo_themes = [theme.get_text(strip=True) for theme in woo_themes_list]

            # Combineer resultaten in een dictionary
            metadata = {
                'titel': title,
                'samenvatting': summary,
                'creatie_jaar': creation_year,
                'woo_themas': woo_themes
            }

            return metadata
            
        except Exception as e:
            print(f"Fout bij genereren metadata: {e}")
            return {
                'titel': 'Onbekend',
                'samenvatting': 'Niet beschikbaar',
                'creatie_jaar': 'Onbekend',
                'woo_themas': []
            }

    def get_filename_from_url(self, url):
        """
        Haalt de originele bestandsnaam uit de URL.
        """
        parsed_url = urlparse(url)
        filename = os.path.basename(unquote(parsed_url.path))
        
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        return filename

    def find_pdfs(self, html_content):
        """
        Zoekt naar PDF links in de HTML content.
        """
        pdf_links = []
        if not html_content:
            return pdf_links
            
        soup = BeautifulSoup(html_content, 'html.parser')
        print("PDF links zoeken...")
        
        # Zoek eerst in de bijlagen sectie
        bijlagen_cell = soup.find('td', string='Bijlagen')
        if bijlagen_cell:
            bijlagen_content = bijlagen_cell.find_next_sibling('td')
            if bijlagen_content:
                links = bijlagen_content.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if href.lower().endswith('.pdf'):
                        filename = self.get_filename_from_url(href)
                        print(f"PDF link gevonden in bijlagen: {filename}")
                        pdf_links.append((href, filename))
        
        return pdf_links

    def download_pdf(self, url, save_path):
        """
        Download een PDF bestand.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"PDF downloaden (poging {attempt + 1}/{max_retries}): {os.path.basename(save_path)}")
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                
                if os.path.getsize(save_path) > 0:
                    print(f"Download succesvol: {os.path.basename(save_path)}")
                    return True
                else:
                    print("Waarschuwing: Gedownload bestand is leeg")
                    os.remove(save_path)
                    
            except Exception as e:
                print(f"Fout bij downloaden PDF (poging {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(2)
        return False

    def create_metadata_file(self, metadata, temp_dir):
        """
        Maakt een metadata tekstbestand aan.
        """
        metadata_path = os.path.join(temp_dir, 'metadata.txt')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write("Document Metadata\n")
            f.write("================\n\n")
            f.write(f"Titel: {metadata['titel']}\n")
            f.write(f"Samenvatting: {metadata['samenvatting']}\n")
            f.write(f"Creatie jaar: {metadata['creatie_jaar']}\n")
            f.write(f"WOO thema's: {', '.join(metadata['woo_themas'])}\n")
        return metadata_path

    def scrape_document(self, url, index):
        """
        Scraped een document URL en slaat alles op in een zip bestand.
        """
        print(f"\n{'='*80}\nDocument {index} verwerken: {url}\n{'='*80}")
        
        # Maak een tijdelijke directory voor de bestanden
        with tempfile.TemporaryDirectory() as temp_dir:
            # Haal de HTML op
            html_content = self.fetch_html(url)
            if not html_content:
                print(f"Kon geen content ophalen voor {url}")
                return

            # Genereer metadata
            metadata = self.generate_metadata(html_content)
            metadata_path = self.create_metadata_file(metadata, temp_dir)
            
            # Zoek PDF links
            pdf_links = self.find_pdfs(html_content)
            if not pdf_links:
                print("Geen PDFs gevonden in document")
                return
            
            print(f"{len(pdf_links)} PDF(s) gevonden om te downloaden")
            
            # Download PDFs naar tijdelijke map
            downloaded_files = []
            for pdf_url, filename in pdf_links:
                save_path = os.path.join(temp_dir, filename)
                if self.download_pdf(pdf_url, save_path):
                    downloaded_files.append(save_path)
            
            # Maak zip bestand
            zip_path = os.path.join(self.base_download_dir, f'woo-{index}.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Voeg metadata toe
                zipf.write(metadata_path, os.path.basename(metadata_path))
                
                # Voeg PDFs toe
                for file_path in downloaded_files:
                    zipf.write(file_path, os.path.basename(file_path))
            
            print(f"Zip bestand aangemaakt: woo-{index}.zip")

    def __del__(self):
        """
        Cleanup Selenium driver bij afsluiten.
        """
        try:
            self.driver.quit()
        except:
            pass