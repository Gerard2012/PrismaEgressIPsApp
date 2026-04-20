#!/usr/bin/env python3

##############################################################################################
# Modules, Global Variables & Config #########################################################
##############################################################################################

import os
import logging
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from src.egress_ips_api import EgressIP

###############################################################################
# Logging
###############################################################################

log_dir = Path("src/logs")
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file),
    ],
)

logger = logging.getLogger(__name__)
logger.info("Application starting")

###############################################################################
# Flask app
###############################################################################

app = Flask(__name__)

###############################################################################
# Azure + Prisma initialization
###############################################################################

def init_prisma_clients():
    keyvault_url = os.getenv("KEYVAULT_URL")

    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=keyvault_url, credential=credential)

    row_api_key = secret_client.get_secret(
        os.getenv("PRISMA_ROW_EGRESS_IP_API_KEY")
    ).value

    cn_api_key = secret_client.get_secret(
        os.getenv("PRISMA_CN_EGRESS_IP_API_KEY")
    ).value

    return {
        "global": {
            "url": os.getenv("PRISMA_ROW_EGRESS_IP_URL"),
            "key": row_api_key,
        },
        "china": {
            "url": os.getenv("PRISMA_CN_EGRESS_IP_URL"),
            "key": cn_api_key,
        },
    }

PRISMA = init_prisma_clients()

###############################################################################
# Helpers
###############################################################################

def get_table_rows(region="global"):
    config = PRISMA.get(region)

    with EgressIP(config["url"], config["key"]) as client:
        api_result = client.fetch_egress_ips()

    rows = []

    for zone_entry in api_result:
        zone = zone_entry.get("zone")

        for detail in zone_entry.get("address_details", []):
            rows.append({
                "zone": zone,
                "service_type": detail.get("serviceType"),
                "address_type": detail.get("addressType"),
                "address": detail.get("address"),
                "node_names": " | ".join(detail.get("node_name", [])),
            })

    return rows


###############################################################################
# Routes
###############################################################################

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/egress-ips")
def egress_ips():
    region = request.args.get("region", "global")
    return jsonify(get_table_rows(region))

###############################################################################
# Entry point (dev only)
###############################################################################

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
