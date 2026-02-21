import sys
sys.path.append(".")
from src.crawlers.paper_downloader_v3 import PaperDownloader

d = PaperDownloader()

# Test the exact case from the data
faculty = "Jessica Bayliss"
authors = ["Penny D. Sackett", "Michaël Gillon", "Daniel D. R. Bayliss", "David T. F. Weldrake", "Brandon Tingley"]

result = d._is_author_match(faculty, authors)

print(f"Faculty: {faculty}")
print(f"Authors: {authors}")
print(f"Match Result: {result}")
print()

if result:
    print("❌ BUG CONFIRMED: Should be False but returned True!")
    print("The function is incorrectly matching 'Jessica Bayliss' with 'Daniel D. R. Bayliss'")
else:
    print("✅ Logic is correct: Returns False as expected")
    print("The issue must be elsewhere in the pipeline")
