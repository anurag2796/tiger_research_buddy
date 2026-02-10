from src.crawlers.rit_crawler import RITCrawler
from rich.console import Console

console = Console()

def test_specific_college(college_name, url):
    console.print(f"\n[bold blue]Testing {college_name} ({url})[/]")
    crawler = RITCrawler()
    
    # 1. Test finding research areas
    areas = crawler._crawl_college_areas(url, college_name)
    console.print(f"Found {len(areas)} areas.")
    for a in areas:
        console.print(f" - {a['name']} ({a['url']})")
    
    if not areas:
        console.print("[red]No areas found (Parsing mismatch?)[/]")
        return
        
    # 2. Test fetching details for ONE area
    sample_area = areas[0]
    console.print(f"Drilling down into: {sample_area['name']} ({sample_area['url']})")
    
    details = crawler.crawl_area_details(sample_area)
    faculty_count = len(details.get('faculty', []))
    console.print(f"Found {faculty_count} faculty in this area.")
    
    if faculty_count == 0:
        console.print("[yellow]Warning: No faculty found (HTML structure might differ)[/]")
    else:
        console.print(f"Sample faculty: {details['faculty'][0]}")

if __name__ == "__main__":
    # Test Engineering - Advanced Manufacturing
    test_specific_college("engineering", "https://www.rit.edu/engineering/research/key-research-areas/advanced-manufacturing")
    
    # Test Science - Imaging Science
    test_specific_college("science", "https://www.rit.edu/science/research/imaging-science")
