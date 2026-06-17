import re

with open("tests/test_bidding_core.py", "r", encoding="utf-8") as f:
    content = f.read()

# Extract ResponseRecommendationTests class
resp_match = re.search(r'class ResponseRecommendationTests\(.*?\):(.*?)(?=\nclass )', content, re.DOTALL)
if resp_match:
    resp_content = resp_match.group(1)
    tests = re.findall(r'def (test_\w+)', resp_content)
    print(f"ResponseRecommendationTests: {len(tests)} tests")
    print("\nFirst 5 tests:")
    for t in tests[:5]:
        print(f"  {t}")
    print("\nLast 5 tests:")
    for t in tests[-5:]:
        print(f"  {t}")
else:
    print("Could not find ResponseRecommendationTests")
