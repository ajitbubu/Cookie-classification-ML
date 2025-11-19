# Dynamic Cookie Scanning Service (DCS)

A Python-based service for scanning domains for cookies, categorizing them, and storing results. Supports deep scans (following internal links) and quick scans (root domain + custom pages). Built with Playwright, Flask, and APScheduler, and runs in Docker.

---

## Features

- Crawl websites to collect cookies and browser storage (localStorage, sessionStorage).
- Categorize cookies using:
  - DB overrides (highest priority)
  - IAB Global Vendor List (GVL)
  - Local JSON rules (cookie_rules.json)
- Distinguish First Party vs Third Party cookies.
- Supports quick scan and deep scan modes.
- Schedule recurring scans using APScheduler.
- Log results to files and optionally to console.
- Dockerized for easy deployment.
- Configurable via environment variables.

## Project Structure

```
dynamic_cookie_scanning/
â”‚â”€â”€ config.py                 # Configurations (API URL, intervals, workers, etc.)
â”‚â”€â”€ config_scanner.py         # Logic to run a scan for a single domain
â”‚â”€â”€ schedule_manager.py       # Scheduler to check API and trigger scans
â”‚â”€â”€ main.py                   # Entrypoint to start the service
â”‚â”€â”€ README.md                 # This file
â”‚â”€â”€ requirements.txt          # Python dependencies
â”‚â”€â”€ config_rules.json         # cookies categorization rules. Should be groomed by DSG team with help of their legal team
â”‚â”€â”€ dcs_api.py                # Flask API for quick scan. Some sample APIs that were used for the development phase
â”‚â”€â”€ docker-compose.yml
â”‚â”€â”€ Dockerfile
â”‚â”€â”€ logger_setup.py           # file for logger related settings
â”‚â”€â”€ test_deep_scanner.py      # file for testing deep scan without docker. need to start flask API first
â”‚â”€â”€ test_quick_scan.py        # file for testing quick scan without docker. need to start flask API first
```

## Installation & Setup

1. Clone the repository

    ```bash
    git clone <repository_url>
    cd <repository_folder>
    ```
<br/>

2. Configurations

    All configurations are in `docker-compose.yml` and `config.py`  
    Port to be exposed for quick scan, URL, can be configured in `config.py` and `docker-compose.yml`.
    
<br/>

3. Build and run Docker container

   <br/>
       ```bash
          sudo docker-compose build
          sudo docker-compose up -d
       ```

     Container name: `dynamic_cookie_scanning`  
     Logs mapped to host: `./logs/dynamic_cookie_scanning.log`
    
<br/>

4. Stop container

    ```bash
    sudo docker-compose down
    ```