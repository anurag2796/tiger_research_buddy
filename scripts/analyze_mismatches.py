import json
from pathlib import Path

# Analyze the mismatch patterns
papers_dir = Path("data/papers")

# Sample recent mismatches
samples = [
    ("carlos_a_multiple_radar", "Carlos Castellanos", ['Carlos Pena-Caballero', 'Osvaldo Castellanos', 'Miguel Rodrigo Castellanos']),
    ("joseph_wideband_dynamic", "Carlos Castellanos", ['Joseph M. Carlson', 'Miguel Rodrigo Castellanos']),
    ("penny_transits_against", "Jessica Bayliss", ['Penny D. Sackett', 'Daniel D. R. Bayliss']),
    ("david_searching_for", "Jessica Bayliss", ['David T. F Weldrake', 'Daniel D. R. Bayliss']),
    ("frank_regression_of", "Reynold Bailey", ['Frank W. Marrs', 'Bailey K. Fosdick']),
]

print("Analyzing Mismatch Patterns:\n")
for filename, faculty, authors in samples:
    print(f"Faculty: {faculty}")
    print(f"Authors: {authors}")
    
    # Check if it's a last name collision
    fac_last = faculty.split()[-1]
    author_lasts = [a.split()[-1] for a in authors]
    
    if fac_last in author_lasts:
        print(f"  ⚠️  LAST NAME COLLISION: '{fac_last}' appears in authors")
        # Find which author
        for author in authors:
            if author.split()[-1] == fac_last:
                fac_first = faculty.split()[0][0]
                auth_first = author.split()[0][0]
                print(f"     Faculty: {faculty} ({fac_first}. {fac_last})")
                print(f"     Author:  {author} ({auth_first}. {author.split()[-1]})")
                if fac_first != auth_first:
                    print(f"     ❌ First initial mismatch: {fac_first} != {auth_first}")
    print()
