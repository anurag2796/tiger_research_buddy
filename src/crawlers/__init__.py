from .smart_crawler import SmartCrawler
from .scholar_crawler import ScholarCrawler, enrich_with_scholar
from .extended_crawler import ExtendedRITCrawler, crawl_extended_sources, add_extended_to_vectorstore
from .pdf_crawler import PDFCrawler, extract_papers_to_vectorstore
from .paper_downloader import PaperDownloader, download_all_papers, index_downloaded_papers

from .phd_crawler import PhDStudentCrawler, crawl_phd_students, add_phd_to_vectorstore

