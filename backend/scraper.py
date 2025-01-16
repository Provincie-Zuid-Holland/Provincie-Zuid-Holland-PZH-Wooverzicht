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
import hashlib

class Scraper:
    """
    Deze class is voor het scrapen en downloaden van documenten van het WOO portaal Overijssel.
    De scraper gebruikt Selenium voor het laden van JavaScript-gerenderde content en BeautifulSoup voor HTML parsing.
    Documenten worden gedownload en opgeslagen in zip bestanden, samen met hun metadata.
    De scraper houdt bij welke bestanden al gedownload zijn om dubbele downloads te voorkomen.
    
    Attributen:
        supported_extensions (tuple): Lijst van ondersteunde bestandsextensies (.pdf, .docx, etc.)
        base_download_dir (str): Basis directory waar de zip bestanden worden opgeslagen
        downloaded_files_cache (dict): Cache van reeds gedownloade bestanden en hun locaties
        driver: Selenium WebDriver instance voor het laden van JavaScript content
        wait: WebDriverWait instance voor het wachten op elementen

    Methodes:
        _build_existing_files_cache() -> dict:
            Bouwt een cache op van alle bestanden die al gedownload zijn in zip bestanden.
            
        _get_file_hash(url: str) -> str:
            Genereert een unieke hash voor een bestands-URL om duplicaten te identificeren.
            
        _is_file_downloaded(filename: str, url: str) -> tuple:
            Controleert of een bestand al eerder is gedownload.
            
        _is_supported_file(url: str) -> bool:
            Controleert of een bestandstype ondersteund wordt voor download.
            
        fetch_html(url: str) -> str:
            Haalt de HTML content op van een pagina, inclusief JavaScript-gerenderde content.
            
        generate_metadata(html_content: str) -> dict:
            Extraheert metadata (titel, samenvatting, jaar, thema's) uit de HTML content.
            
        get_filename_from_url(url: str) -> str:
            Genereert een unieke en geldige bestandsnaam uit een URL.
            
        find_documents(html_content: str) -> list:
            Vindt alle downloadbare documenten in de HTML content.
            
        download_document(url: str, save_path: str) -> bool:
            Download een document met foutafhandeling en retries.
            
        create_metadata_file(metadata: dict, temp_dir: str) -> str:
            Maakt een tekstbestand met metadata informatie.
            
        scrape_document(url: str, index: int) -> None:
            Hoofdfunctie die een document URL scraped en alle gevonden bestanden downloadt.
            
    Details:
        - De scraper gebruikt een cache systeem om bij te houden welke bestanden al zijn gedownload
        - Bestanden worden opgeslagen in zip files met de naam 'woo-{index}.zip'
        - Elk zip bestand bevat de gedownloade documenten en een metadata.txt bestand
        - Ondersteunde bestandsformaten zijn configureerbaar via supported_extensions
        - De scraper probeert maximaal 3 keer om een bestand te downloaden bij fouten
        - Alle interactie gebeurt met Nederlandse logging voor duidelijke feedback
        - Tijdelijke bestanden worden automatisch opgeruimd na verwerking
    """    
    def __init__(self):
        """
        Initialiseert de Scraper met de basis mapstructuur en houdt een cache bij van gedownloade bestanden.
        """
        # Lijst met ondersteunde bestandsformaten
        self.supported_extensions = ('.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.csv', '.rtf')
        
        # Maak de basis download directory aan voor de zip files
        self.base_download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'data','downloads')
        os.makedirs(self.base_download_dir, exist_ok=True)
        
        # Cache voor het bijhouden van gedownloade bestanden
        self.downloaded_files_cache = self._build_existing_files_cache()
        
        # Selenium configuratie
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 20)

    def _build_existing_files_cache(self):
        """
        Bouwt een cache op van bestaande bestanden in zip files.
        """
        cache = {}
        try:
            for filename in os.listdir(self.base_download_dir):
                if filename.endswith('.zip'):
                    zip_path = os.path.join(self.base_download_dir, filename)
                    with zipfile.ZipFile(zip_path, 'r') as zipf:
                        for file_info in zipf.filelist:
                            if file_info.filename.lower().endswith(self.supported_extensions):
                                cache[file_info.filename] = zip_path
        except Exception as e:
            print(f"Waarschuwing: Fout bij opbouwen cache: {e}")
        return cache

    def _get_file_hash(self, url):
        """
        Genereert een unieke hash voor een bestands-URL.
        """
        return hashlib.md5(url.encode()).hexdigest()

    def _is_file_downloaded(self, filename, url):
        """
        Controleert of een bestand al is gedownload.
        """
        if filename in self.downloaded_files_cache:
            return True, self.downloaded_files_cache[filename]
        
        file_hash = self._get_file_hash(url)
        for existing_file, zip_path in self.downloaded_files_cache.items():
            if existing_file.startswith(file_hash):
                return True, zip_path
                
        return False, None

    def _is_supported_file(self, url):
        """
        Controleert of het bestandstype ondersteund wordt.
        """
        return url.lower().endswith(self.supported_extensions)

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
            return {
                'titel': title,
                'samenvatting': summary,
                'creatie_jaar': creation_year,
                'woo_themas': woo_themes
            }
            
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
        Haalt de originele bestandsnaam uit de URL en voegt hash toe voor uniekheid.
        """
        parsed_url = urlparse(url)
        original_filename = os.path.basename(unquote(parsed_url.path))
        
        # Verwijder ongeldige karakters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            original_filename = original_filename.replace(char, '_')
        
        # Voeg hash toe aan bestandsnaam voor unieke identificatie
        file_hash = self._get_file_hash(url)
        filename_parts = os.path.splitext(original_filename)
        return f"{file_hash}_{filename_parts[0]}{filename_parts[1]}"

    def find_documents(self, html_content):
        """
        Zoekt naar alle ondersteunde documenttypes in de HTML content.
        """
        doc_links = []
        if not html_content:
            return doc_links
            
        soup = BeautifulSoup(html_content, 'html.parser')
        print("Document links zoeken...")
        
        # Zoek eerst in de bijlagen sectie
        bijlagen_cell = soup.find('td', string='Bijlagen')
        if bijlagen_cell:
            bijlagen_content = bijlagen_cell.find_next_sibling('td')
            if bijlagen_content:
                links = bijlagen_content.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if self._is_supported_file(href):
                        filename = self.get_filename_from_url(href)
                        extension = os.path.splitext(href.lower())[1]
                        print(f"{extension.upper()[1:]} bestand gevonden in bijlagen: {filename}")
                        doc_links.append((href, filename))
        
        # Als backup ook zoeken in hele document
        if not doc_links:
            for link in soup.find_all('a', href=True):
                href = link['href']
                if self._is_supported_file(href):
                    filename = self.get_filename_from_url(href)
                    extension = os.path.splitext(href.lower())[1]
                    print(f"{extension.upper()[1:]} bestand gevonden: {filename}")
                    doc_links.append((href, filename))
        
        return doc_links

    def download_document(self, url, save_path):
        """
        Download een document met verbeterde error handling.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Document downloaden (poging {attempt + 1}/{max_retries}): {os.path.basename(save_path)}")
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                
                if os.path.getsize(save_path) > 0:
                    extension = os.path.splitext(save_path)[1].upper()[1:]
                    print(f"{extension} bestand succesvol gedownload: {os.path.basename(save_path)}")
                    return True
                else:
                    print("Waarschuwing: Gedownload bestand is leeg")
                    os.remove(save_path)
                    
            except Exception as e:
                print(f"Fout bij downloaden (poging {attempt + 1}): {e}")
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
            f.write(f"Titel: {metadata['titel']}\n")
            f.write(f"Samenvatting: {metadata['samenvatting']}\n")
            f.write(f"Creatie jaar: {metadata['creatie_jaar']}\n")
            f.write(f"WOO thema's: {', '.join(metadata['woo_themas'])}\n")
        return metadata_path

    def scrape_document(self, url, index):
        """
        Scraped een document URL en slaat alle gevonden bestanden op in een zip bestand.
        """
        print(f"\n{'='*80}\nDocument {index} verwerken: {url}\n{'='*80}")
        
        # Controleer of zip bestand al bestaat
        zip_path = os.path.join(self.base_download_dir, f'woo-{index}.zip')
        if os.path.exists(zip_path):
            print(f"Zip bestand woo-{index}.zip bestaat al")
            return

        # Maak een tijdelijke directory voor de bestanden
        with tempfile.TemporaryDirectory() as temp_dir:
            html_content = self.fetch_html(url)
            if not html_content:
                print(f"Kon geen content ophalen voor {url}")
                return

            # Genereer en sla metadata op
            metadata = self.generate_metadata(html_content)
            metadata_path = self.create_metadata_file(metadata, temp_dir)
            
            # Zoek alle document links
            doc_links = self.find_documents(html_content)
            if not doc_links:
                print("Geen documenten gevonden")
                return
            
            print(f"{len(doc_links)} document(en) gevonden om te downloaden")
            
            # Download alleen nieuwe bestanden
            downloaded_files = []
            skipped_files = []
            for doc_url, filename in doc_links:
                is_downloaded, existing_zip = self._is_file_downloaded(filename, doc_url)
                if is_downloaded:
                    print(f"Bestand {filename} is al gedownload in {existing_zip}")
                    skipped_files.append((filename, existing_zip))
                    continue

                save_path = os.path.join(temp_dir, filename)
                if self.download_document(doc_url, save_path):
                    downloaded_files.append(save_path)
                    # Update cache met nieuw bestand
                    self.downloaded_files_cache[filename] = zip_path
            
            # Maak alleen een zip bestand als er nieuwe bestanden zijn
            if downloaded_files:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Voeg metadata toe
                    zipf.write(metadata_path, os.path.basename(metadata_path))
                    
                    # Voeg nieuwe bestanden toe
                    for file_path in downloaded_files:
                        zipf.write(file_path, os.path.basename(file_path))
                
                print(f"Zip bestand aangemaakt: woo-{index}.zip")
                print(f"Aantal nieuwe bestanden: {len(downloaded_files)}")
                print(f"Aantal overgeslagen bestanden: {len(skipped_files)}")
            else:
                print("Geen nieuwe bestanden om te downloaden")

    def __del__(self):
        """
        Cleanup Selenium driver bij afsluiten.
        """
        try:
            self.driver.quit()
        except:
            pass