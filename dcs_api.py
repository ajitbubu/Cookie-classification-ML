from flask import Flask, jsonify, request
from datetime import datetime
import os
import json
import time
import logging
from config import SCAN_MAX_RETRY_DEFAULT
from logger_setup import setup_logger
from collections import OrderedDict
logger = setup_logger()


# Import cookie_scanner
from cookie_scanner import quick_scan_domain, _build_result

app = Flask(__name__)

RESULTS_DIR = os.environ.get("RESULTS_DIR", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

#logger = logging.getLogger(__name__)

@app.route("/api/schedules", methods=["GET"])
def get_schedules():
    now = datetime.now()
    return jsonify(
        {
            "message": "Data Extracted Successfully!!!",
            "data": [
                {
                    "domain_config_id": "b6b2d737-63ad-44cb-afc3-989dfb1b5516",
                    "data": {
                        "domain": "https://ir.exlservice.com",
                        "description": "",
                        "schedule": {
                            "frequency": "Hourly",
                            "time": {
                                "minute": 15,
                            }
                        },
                        "maxPages": 5,
                        "scanDepth": 1,
                        "maxRetries": 3,
                        "domain_config_id": "b6b2d737-63ad-44cb-afc3-989dfb1b5516",
                        "allow_deep_scan": "true"
                    }
                },
                # {
                #     "domain_config_id": "b6b2d737-63ad-44cb-afc3-989dfb1b5516",
                #     "data": {
                #         "domain": "https://www.cricbuzz.com",
                #         "description": "",
                #         "schedule": {
                #             "frequency": "Weekly",
                #             "time": {
                #                 "day": "Friday",
                #                 "hour": 15 ,
                #                 "minute": 15,
                #             }
                #         },
                #         "maxPages": 5,
                #         "scanDepth": 1,
                #         "maxRetries": 3,
                #         "domain_config_id": "b6b2d737-63ad-44cb-afc3-989dfb1b5516",
                #         "allow_deep_scan": "true"
                #     }
                # },
                # {
                #     "domain_config_id": "b6b2d737-63ad-44cb-afc3-989dfb1b5516",
                #     "data": {
                #         "domain": "https://www.cricbuzz.com",
                #         "description": "",
                #         "schedule": {
                #             "frequency": "Monthly",
                #             "time": {
                #                 "day": 30,
                #                 "hour": 15 ,
                #                 "minute": 15,
                #             }
                #         },
                #         "maxPages": 5,
                #         "scanDepth": 1,
                #         "maxRetries": 3,
                #         "domain_config_id": "b6b2d737-63ad-44cb-afc3-989dfb1b5516",
                #         "allow_deep_scan": "true"
                #     }
                # },
                {
                    "domain_config_id": "9162f59e-ce11-46b7-93be-49e771496db2",
                    "data": {
                        "domain": "https://www.exlservice.com",
                        "description": "ABCD",
                        "schedule": {
                            "frequency": "Hourly",
                            "time": {
                                "minute": 20
                            }
                        },
                        "maxPages": 5,
                        "scanDepth": 2,
                        "maxRetries": 3,
                        "customPages": [
                            "/about"
                        ],
                        "domain_config_id": "9162f59e-ce11-46b7-93be-49e771496db2",
                        "allow_deep_scan": "true"
                    }
                }
            ],
            "status_code": 200
        }    
    )

@app.route("/api/results", methods=["POST"])
def receive_results():
    """
    Receive scan JSON and write to file per domain with timestamp.
    Body expected: JSON object (dict) containing at least 'domain' key.
    """
    try:
        payload = request.get_json(force=True)
        #print("Received data:", payload)  # log payload
    except Exception as e:
        print(jsonify({"error": "invalid json", "details": str(e)}))
        return jsonify({"error": "invalid json", "details": str(e)}), 400

    domain = payload.get("domain") or payload.get("job_id") or "unknown"
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_domain = domain.replace("/", "_").replace(":", "_")
    filename = f"{safe_domain}_{ts}.json"
    path = os.path.join(RESULTS_DIR, filename)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return jsonify({"error": "failed to write result", "details": str(e)}), 500

    return jsonify({"status": "ok", "file": filename}), 201


@app.route("/api/fetch-domain-cookie-categorization", methods=["GET"])
def get_domain_cookie_categorization():
    """
    Get cookie categorization for a given domain.
    Example: /api/fetch-domain-cookie-categorization?domain=exlservice.com
    Response aligns with categorize_cookie expectations.
    """
    domain_config_id = request.args.get("domain_config_id", "").lower().strip()
    if not domain_config_id:
        return jsonify({"error": "Missing 'domain_config_id' parameter"}), 400

    return jsonify(
        {
            "message": "Data Extracted Successfully!!!",
            "data": {
                "_id": "68cbbfde293e8fdfabba3b20",
                "domain_config_id": "912579a1-8847-47bb-bd2b-28430cd115e3",
                "domain": "https://www.exlservice.com",
                "timestamp_utc": "2025-09-18T08:16:30Z",
                "params": {
                    "maxPages": 5,
                    "scanDepth": 5,
                    "maxRetries": 5,
                    "customPages": [
                        "/about"
                    ]
                },
                "pages_visited": [
                    "https://www.exlservice.com/#main-content",
                    "https://www.exlservice.com/",
                    "https://www.exlservice.com/about-exl",
                    "https://www.exlservice.com/about",
                    "https://www.exlservice.com/about-exl#main-content",
                    "https://www.exlservice.com"
                ],
                "total_cookies": 44,
                "page_count": 6,
                "attempt": 1,
                "status": "success",
                "error": "null",
                "duration_seconds": 89.29712772369385,
                "cookies": [
                    {
                        "name": "visid_incap_2666558",
                        "domain": ".exlservice.com",
                        "path": "/",
                        "hashed_value": "4a5fa60f9812fbbade00e5ad7fdd8657afe0a79f82925e073218db474d967359",
                        "expiry": 1789661264.904382,
                        "size": 64,
                        "httpOnly": "true",
                        "secure": "true",
                        "sameSite": "None",
                        "party": "First Party",
                        "set_after_accept": "false",
                        "category": "marketing",
                        "vendor": "",
                        "iab_purposes": [
                            1
                        ],
                        "description": "Incapsula security cookies (load balancing, bot protection).",
                        "source": "RulesJSON"
                    },
                    {
                        "name": "nlbi_2666558",
                        "domain": ".exlservice.com",
                        "path": "/",
                        "hashed_value": "7faa4efbbcbfd50ab48a93db11975d9967e4836875cf204802930ae52b8e16b8",
                        "expiry": -1,
                        "size": 48,
                        "httpOnly": "true",
                        "secure": "true",
                        "sameSite": "None",
                        "party": "First Party",
                        "set_after_accept": "false",
                        "category": "necessary",
                        "vendor": "",
                        "iab_purposes": [
                            1
                        ],
                        "description": "Incapsula security cookies (load balancing, bot protection).",
                        "source": "RulesJSON"
                    },
                    {
                        "name": "incap_ses_737_2666558",
                        "domain": ".exlservice.com",
                        "path": "/",
                        "hashed_value": "f1d66ed340ba1aa583dbd6d40cd50d973b74572802840437e78b1abf5909087b",
                        "expiry": -1,
                        "size": 56,
                        "httpOnly": "false",
                        "secure": "true",
                        "sameSite": "None",
                        "party": "First Party",
                        "set_after_accept": "false",
                        "category": "necessary",
                        "vendor": "",
                        "iab_purposes": [
                            1
                        ],
                        "description": "Incapsula security cookies (load balancing, bot protection).",
                        "source": "RulesJSON"
                    },
                    {
                        "name": "_clsk",
                        "domain": ".exlservice.com",
                        "path": "/",
                        "hashed_value": "4e251da83a667cb1c9e0d3a87e84547bb0d40662f3ddb444034fbc72340f9064",
                        "expiry": 1758269782,
                        "size": 56,
                        "httpOnly": "false",
                        "secure": "false",
                        "sameSite": "Lax",
                        "party": "First Party",
                        "set_after_accept": "false",
                        "category": "analytics",
                        "vendor": "",
                        "iab_purposes": [
                            7
                        ],
                        "description": "Microsoft Clarity tracking cookies.",
                        "source": "RulesJSON"
                    }
                ],
                "storages": {
                    "localStorage": {
                        "showBottomSearchBar": "b5bea41b6c623f7c09f1bf24dcae58ebab3c0cdd90ad966bc43a45b44867e12b",
                        "reese84": "b339e3327b0737949863fd94957f0145cc7988d88ad366484e512c4a56f7bb13",
                        "_gcl_ls": "cc5d4aa0d1c8e1a07909c0b45f824b28fe0fc50a27c964e4fdd83e61012f779a",
                        "dsghash": "a13c1528750a2d0ef4bdc62c305a7c352485a6215807f27ce726c73544878b7b",
                        "li_adsId": "5f9347e8307b9efa757eaa6b7f96821ed795a59365ab62352421318ca72bd2de"
                    },
                    "sessionStorage": {
                        "_cltk": "cb8880faffb1c12f68f0c6b16670dbe22a833b714d63027d381bd4586264cdef",
                        "ziPendingTelemetry": "555afc9cc24e9b0efc13856c26d0b69910165880a8607c2a8df70b54e4ac03b3",
                        "visitor_id": "bf6dcd8bc30fcf889023a914239241aaaa176b57aa118adfc0e71ae12a158878"
                    }
                },
                "scan_mode": "deep",
                "version": 16
            },
            "status_code": 200
        }

    )


# ---------------- Quick-scan endpoint ----------------
@app.route("/api/quick-scan", methods=["POST"])
def quick_scan():
    """
    Quick scan endpoint used by UI.
    Accepts JSON body:
      {
        "domainUrl": "https://example.com",   # required
        "customPages": ["/about","/contact"], # optional
        "maxRetries": 2,                      # optional (default handled by scanner)
      }

    Returns: the scan result JSON (same shape as deep-scan _build_result).
    This endpoint calls cookie_scanner.quick_scan_domain(...) and returns its result inline.
    """
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        logger.exception("Invalid JSON for quick-scan")
        return jsonify({"error": "invalid json", "details": str(e)}), 400

    if not payload:
        return jsonify({"error": "empty request body"}), 400

    domain_url = payload.get("domain")
    if not domain_url:
        return jsonify({"error": "domain is required"}), 400

    custom_pages = payload.get("customPages", [])
    max_retries = int(payload.get("maxRetries", SCAN_MAX_RETRY_DEFAULT))
 
    domain_id = payload.get("_id")
    domain_config_id = payload.get("domain_config_id")

    # Prepare a domain-like schedule dict for _build_result compatibility
    domain_req = {
        "_id": domain_id,
        "domain_config_id": domain_config_id,
        "domainUrl": domain_url,
        "customPages": custom_pages,
        "maxRetries": max_retries,
    }

    logger.info(f"[QUICK_SCAN_REQ] domain={domain_url} custom_pages={custom_pages} maxRetries={max_retries}")

    try:
        # use the quick-scan wrapper in cookie_scanner (should return result dict)
        # We expect cookie_scanner.quick_scan_domain(domain_req) to exist and return the _build_result-shaped dict
        result = quick_scan_domain(domain_req)

        # ensure scan_mode marker for clarity
        if isinstance(result, dict):
            result["scan_mode"] = "quick"
        return jsonify(OrderedDict(result)), 200

    except Exception as e:
        logger.exception("Quick-scan failed")
        failed = _build_result(domain_req, {"cookies": [], "storages": {}, "pages_visited": []}, attempt=1, status="failed", error=str(e), duration=None)
        failed["scan_mode"] = "quick"
        return jsonify({"error": "quick-scan failed", "details": str(e), "result": failed}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9010)

