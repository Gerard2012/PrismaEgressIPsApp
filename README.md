# MVNAIP - *Multi‑Vendor Network Automation &amp; Insights Platform*
 
Build a unified automation system that:

- Pulls telemetry and configuration info from Cisco Catalyst Center
- Pulls SD‑WAN and security posture data from Prisma APIs
- Correlates, normalizes, and visualizes the data
- Automates a network workflow (e.g., provisioning, policy enforcement, compliance check)
- Uses webhooks/events for reactive automation
- Follows DevOps/dev‑best practices expected in AUTOCOR



✅ Installing and Running the Docker Container
Below are the full step‑by‑step instructions for building and running this project using Docker and Docker Compose.

📦 1. Prerequisites
Make sure you have the following installed:

Docker Engine
Docker Compose (included automatically with modern Docker versions)

Verify installation:
Shelldocker --versiondocker compose versionShow more lines

📁 2. Project Structure
This repository should look like this:
my-python-project/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
└── src/
    ├── tests/
    ├── logs/
    ├── main.py
    ├── util.py
    └── config.json


Dockerfile → Defines how the Docker image is built
docker-compose.yml → Defines how the container runs
requirements.txt → Python dependencies
.env → Environment variables passed into the container
src/ → Source code, including main.py


🔧 3. Add Environment Variables
Create a .env file in the project root.
Example:
Plain Textenv isn’t fully supported. Syntax highlighting is based on Plain Text.API_KEY=your-api-key-hereENV_NAME=productionShow more lines

Note: Do not commit .env to Git if it contains secrets.


🛠️ 4. Build the Docker Image
From the project root:
Shelldocker compose buildShow more lines
This will:

Read the Dockerfile
Install dependencies from requirements.txt
Copy your Python code into the image


▶️ 5. Run the Application
Start the container:
Shelldocker compose upShow more lines
Or run in the background:
Shelldocker compose up -dShow more lines
The container will:

Load environment variables from .env
Execute
Shellpython src/main.pyShow more lines



🧪 6. Run a One‑Off Command (Optional)
To run any custom Python script inside the container:
Shelldocker compose run --rm app python src/main.pyShow more lines
Or another script:
Shelldocker compose run --rm app python src/tests/test_script.pyShow more lines

📜 7. View Logs
If you ran in the background:
Shelldocker compose logs -fShow more lines
You can also view log files under:
src/logs/

(These are mounted from the container.)

🛑 8. Stop Containers
Stop and remove containers:
Shelldocker compose downShow more lines
Stop without removing volumes:
Shelldocker compose stopShow more lines

🧹 9. (Optional) Remove Image & Clean Up
Shelldocker compose down --rmi alldocker system prune -fShow more lines

If you'd like, I can also produce: