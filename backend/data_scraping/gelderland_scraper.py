import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, unquote, urljoin
import zipfile
import tempfile
import hashlib
import re


class Scraper:
    """
    Deze class is voor het scrapen en downloaden van documenten van het WOO portaal Gelderland.
    De scraper gebruikt requests en BeautifulSoup voor HTML parsing.
    Documenten worden gedownload en opgeslagen in zip bestanden, samen met hun metadata.
    De scraper houdt bij welke bestanden al gedownload zijn om dubbele downloads te voorkomen.

    Attributen:
        supported_extensions (tuple): Lijst van ondersteunde bestandsextensies (.pdf, .docx, etc.)
        base_download_dir (str): Basis directory waar de zip bestanden worden opgeslagen
        downloaded_files_cache (dict): Cache van reeds gedownloade bestanden en hun locaties
        session: Requests session voor het hergebruiken van verbindingen
        headers (dict): HTTP headers voor requests

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
            Haalt de HTML content op van een pagina.

        generate_metadata(html_content: str, url: str) -> dict:
            Extraheert metadata uit de HTML content.

        get_filename_from_url(url: str) -> str:
            Genereert een unieke en geldige bestandsnaam uit een URL.

        find_documents(html_content: str, url: str) -> list:
            Vindt alle downloadbare documenten in de HTML content.

        download_document(url: str, save_path: str) -> bool:
            Download een document met foutafhandeling en retries.

        create_metadata_file(metadata: dict, temp_dir: str) -> str:
            Maakt een tekstbestand met metadata informatie.

        scrape_document(url: str, index: int) -> None:
            Hoofdfunctie die een document URL scraped en alle gevonden bestanden downloadt.
    """

    def __init__(self):
        """
        Initialiseert de Scraper met de basis mapstructuur en houdt een cache bij van gedownloade bestanden.
        """
        # Lijst met ondersteunde bestandsformaten
        self.supported_extensions = (
            ".pdf",
            ".docx",
            ".doc",
            ".xlsx",
            ".xls",
            ".pptx",
            ".ppt",
            ".txt",
            ".csv",
            ".rtf",
        )

        # Maak de basis download directory aan voor de zip files met provincie subfolder
        downloads_base = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data_scraping", "downloads"
        )
        self.base_download_dir = os.path.join(downloads_base, "gelderland")
        os.makedirs(self.base_download_dir, exist_ok=True)

        # Cache voor het bijhouden van gedownloade bestanden
        self.downloaded_files_cache = self._build_existing_files_cache()

        # Requests sessie voor hergebruik van verbindingen
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        }

    def _build_existing_files_cache(self):
        """
        Bouwt een cache op van bestaande bestanden in zip files.
        """
        cache = {}
        try:
            for filename in os.listdir(self.base_download_dir):
                if filename.endswith(".zip"):
                    zip_path = os.path.join(self.base_download_dir, filename)
                    with zipfile.ZipFile(zip_path, "r") as zipf:
                        for file_info in zipf.filelist:
                            if file_info.filename.lower().endswith(
                                self.supported_extensions
                            ):
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
        Haalt HTML content op met requests.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"HTML ophalen (poging {attempt + 1}/{max_retries})")
                response = self.session.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response.text

            except Exception as e:
                print(f"Fout bij ophalen HTML (poging {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2)
        return None

    def generate_metadata(self, html_content, url):
        """
        Genereert metadata van de HTML content.
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            metadata = {
                "url": url,
                "titel": "Onbekend",
                "samenvatting": "Niet beschikbaar",
                "creatie_jaar": "Onbekend",
                "woo_themas": [],
            }

            # Probeer titel te vinden (h1 is meest waarschijnlijk)
            title_tag = soup.find("h1")
            if title_tag:
                metadata["titel"] = title_tag.get_text(strip=True)
            else:
                # Als alternatief, probeer de titel uit de URL te halen
                parsed_url = urlparse(url)
                path_segments = parsed_url.path.split("/")
                if len(path_segments) > 2:
                    url_title = path_segments[-1].replace("-", " ")
                    if url_title:
                        metadata["titel"] = url_title.capitalize()

            # Probeer samenvatting/beschrijving te vinden
            desc_candidates = [
                soup.select_one(".summary, .description, .intro"),
                soup.find("meta", property="og:description"),
                soup.find("meta", attrs={"name": "description"}),
            ]

            for candidate in desc_candidates:
                if candidate:
                    if candidate.name == "meta":
                        metadata["samenvatting"] = candidate.get("content", "").strip()
                    else:
                        metadata["samenvatting"] = candidate.get_text(strip=True)
                    break

            # Probeer het jaar te vinden
            # Zoek naar een datum in de tekst
            date_tags = soup.select(".date, time, .datum")
            if date_tags:
                date_text = date_tags[0].get_text(strip=True)
                # Probeer het jaar eruit te halen
                year_match = re.search(r"20\d{2}", date_text)
                if year_match:
                    metadata["creatie_jaar"] = year_match.group(0)

            # Als alternatief, zoek jaar in URL
            if metadata["creatie_jaar"] == "Onbekend":
                year_match = re.search(r"20\d{2}", url)
                if year_match:
                    metadata["creatie_jaar"] = year_match.group(0)

            # Probeer thema's te vinden
            themes_list = soup.select(".categories a, .tags a, .themas a")
            metadata["woo_themas"] = (
                [theme.get_text(strip=True) for theme in themes_list]
                if themes_list
                else []
            )

            return metadata

        except Exception as e:
            print(f"Fout bij genereren metadata: {e}")
            return {
                "url": url,
                "titel": "Onbekend",
                "samenvatting": "Niet beschikbaar",
                "creatie_jaar": "Onbekend",
                "woo_themas": [],
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
            original_filename = original_filename.replace(char, "_")

        # Als bestandsnaam leeg of ongeldig is, probeer van Content-Disposition header
        if (
            not original_filename
            or original_filename == "_"
            or "." not in original_filename
        ):
            try:
                head_response = self.session.head(url, headers=self.headers, timeout=10)
                content_disposition = head_response.headers.get("content-disposition")
                if content_disposition:
                    filename_match = re.search(
                        r'filename="?([^";]+)', content_disposition
                    )
                    if filename_match:
                        original_filename = filename_match.group(1)
                        for char in invalid_chars:
                            original_filename = original_filename.replace(char, "_")
            except Exception as e:
                print(f"Kon Content-Disposition niet ophalen: {e}")

        # Als we nog steeds geen goede bestandsnaam hebben, gebruik generieke naam met extensie
        if (
            not original_filename
            or original_filename == "_"
            or "." not in original_filename
        ):
            # Probeer extensie te bepalen uit URL
            extension = ".pdf"  # Default extensie
            for ext in self.supported_extensions:
                if url.lower().endswith(ext):
                    extension = ext
                    break

            original_filename = f"document{extension}"

        # Voeg hash toe aan bestandsnaam voor unieke identificatie
        file_hash = self._get_file_hash(url)
        filename_parts = os.path.splitext(original_filename)
        return f"{file_hash}_{filename_parts[0]}{filename_parts[1]}"

    def find_documents(self, html_content, url):
        """
        Zoekt naar alle ondersteunde documenttypes in de HTML content.
        """
        doc_links = []
        if not html_content:
            return doc_links

        soup = BeautifulSoup(html_content, "html.parser")
        print("Document links zoeken...")

        # Zoek eerst in specifieke bijlage/download secties
        attachment_sections = [
            soup.select(".attachments, .bijlagen, .downloads, .documenten"),
            soup.select(".document-list, .files-list, .downloads-list"),
        ]

        for section_list in attachment_sections:
            if section_list:
                for section in section_list:
                    links = section.find_all("a", href=True)
                    for link in links:
                        href = link["href"]
                        absolute_url = urljoin(url, href)
                        if self._is_supported_file(absolute_url):
                            filename = self.get_filename_from_url(absolute_url)
                            extension = os.path.splitext(absolute_url.lower())[1]
                            print(
                                f"{extension.upper()[1:]} bestand gevonden in bijlagen: {filename}"
                            )
                            doc_links.append((absolute_url, filename))

        # Als backup ook zoeken in hele document
        if not doc_links:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(url, href)
                if self._is_supported_file(absolute_url):
                    # Zoek naar context die suggereert dat het om een download gaat
                    download_indicators = [
                        "download",
                        "bijlage",
                        "document",
                        "bestand",
                        "pdf",
                        "doc",
                        "xls",
                    ]

                    link_text = link.get_text(strip=True).lower()
                    link_classes = (
                        " ".join(link.get("class", [])).lower()
                        if link.get("class")
                        else ""
                    )

                    is_download_link = any(
                        indicator in link_text
                        or indicator in link_classes
                        or indicator in href.lower()
                        for indicator in download_indicators
                    )

                    if is_download_link:
                        filename = self.get_filename_from_url(absolute_url)
                        extension = os.path.splitext(absolute_url.lower())[1]
                        print(f"{extension.upper()[1:]} bestand gevonden: {filename}")
                        doc_links.append((absolute_url, filename))

        return doc_links

    def download_document(self, url, save_path):
        """
        Download een document met verbeterde error handling.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(
                    f"Document downloaden (poging {attempt + 1}/{max_retries}): {os.path.basename(save_path)}"
                )
                response = self.session.get(
                    url, stream=True, headers=self.headers, timeout=30
                )
                response.raise_for_status()

                with open(save_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)

                if os.path.getsize(save_path) > 0:
                    extension = os.path.splitext(save_path)[1].upper()[1:]
                    print(
                        f"{extension} bestand succesvol gedownload: {os.path.basename(save_path)}"
                    )
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
        metadata_path = os.path.join(temp_dir, "metadata.txt")
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {metadata.get('url', 'Onbekend')}\n")
            f.write(f"Titel: {metadata.get('titel', 'Onbekend')}\n")
            f.write(
                f"Samenvatting: {metadata.get('samenvatting', 'Niet beschikbaar')}\n"
            )
            f.write(f"Creatie jaar: {metadata.get('creatie_jaar', 'Onbekend')}\n")
            f.write(f"WOO thema's: {', '.join(metadata.get('woo_themas', []))}\n")
            f.write(f"Verzameld op: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        return metadata_path

    def scrape_document(self, url, index):
        """
        Scraped een document URL en slaat alle gevonden bestanden op in een zip bestand.
        """
        print(f"\n{'='*80}\nDocument {index} verwerken: {url}\n{'='*80}")

        # Controleer of zip bestand al bestaat
        zip_path = os.path.join(self.base_download_dir, f"woo-{index}.zip")
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
            metadata = self.generate_metadata(html_content, url)
            metadata_path = self.create_metadata_file(metadata, temp_dir)

            # Zoek alle document links
            doc_links = self.find_documents(html_content, url)
            if not doc_links:
                print("Geen documenten gevonden")
                return

            print(f"{len(doc_links)} document(en) gevonden om te downloaden")

            # Download alleen nieuwe bestanden
            downloaded_files = []
            skipped_files = []
            for doc_url, filename in doc_links:
                is_downloaded, existing_zip = self._is_file_downloaded(
                    filename, doc_url
                )
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
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
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
        Cleanup bij afsluiten.
        """
        try:
            self.session.close()
        except:
            pass
