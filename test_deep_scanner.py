import logging
from cookie_scanner import scan_domain

# Configure logging to see info
logging.basicConfig(level=logging.INFO)

# Fake domain schedule like the scheduler would send
domain_schedule = {
    "_id": "1",
    "domainUrl": "https://www.exlservice.com",   # <--- change to your test site
    "scanDepth": 2,
    "maxPages": 5,                        # small for testing
    "maxRetries": 3,
    "customPages": ["/industries/banking-and-capital-markets/capital-markets"],  # optional
    "accept_selector": 'button[data-role="accept"]'
}

if __name__ == "__main__":
    result = scan_domain(domain_schedule)
    print("Final scan result:")
    print(result)
