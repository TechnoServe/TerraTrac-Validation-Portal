# eudr-comply-api

API to validate farm locations from deforestation zone found in Global Forest Watch database

## Prerequisites

Before you begin, make sure you have the following installed:

- Python (3.6 or higher)
- Pip (Python package installer)
- Virtualenv (optional, but recommended)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/TechnoServe/eudr-comply-api.git
   cd eudr-comply-api

   ```

2. **Create a virtual environment:**

   ```bash
   virtualenv venv
   source venv/Scripts/activate
   ```

3. **Install the dependencies:**

   ```bash
    pip install -r requirements.txt
   ```

4. **Set the environment variables:**

   ```bash
   GFW_USERNAME=<your global forest watch account username>
   GFW_PASSWORD=<your global forest watch account password>
   API_BASE_URL=https://data-api.globalforestwatch.org
   EMAIL=<your email>
   ORGANIZATION=TNS
   DOMAINS=[]
   API_KEY=<your api key>
   ```

5. **Run the application:**

   ```bash
   python manage.py runserver
   ```

6. **Access different routes:**

   **_Access Admin Panel:_**

   ```bash
   127.0.0.1:8000/admin
   ```

   **_Access API:_**

   \***\*POST Request:\*\***

   Make requests to postman or any other API testing tool with the following parameters:

   ```bash
   URL:
   127.0.0.1:8000/api/get-radd-data/

   Headers:
   Content-Type: application/json

   Body:
   {
    "geometry": {
        "coordinates": [<add points or polygon array of points>],
        "type": "Polygon"
    },
    "sql": "SELECT longitude, latitude, wur_radd_alerts__date, wur_radd_alerts__confidence FROM results WHERE wur_radd_alerts__date >= '2021-01-01'"}
   ```
