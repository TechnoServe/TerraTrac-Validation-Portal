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
    cd api/eudrAPI
    python manage.py runserver
    ```
