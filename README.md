# TerraTrac Validation Portal

The **TerraTrac Validation Portal** is a Django REST Framework-based web application designed to upload farm-related data, process it through a third-party API for validation, and allow users to view the analyzed results on an interactive map. The app also supports exporting the analyzed data in various formats such as CSV, GeoJSON, and PDF. It is for the purpose of helping farmers and agricultural organizations to be ready for EUDR compliance which will start to act from 1st january 2024.

## Features

- **Data Upload**: Users can upload farm data via CSV or GeoJSON files.
- **Third-Party API Integration**: Collected data is validated and processed through an external API called [Whisp](https://whisp.openforis.org/documentation).
- **Interactive Map**: Processed data is displayed on an interactive map for users to view.
- **Data Export**: Users can export the analyzed data in multiple formats including CSV, GeoJSON, and PDF and that file will be exported with commodities to EU authorities.

## Requirements

To get started with the project, ensure you have the following installed:

- Python 3.12+
- Django 5.0.8+
- Django REST Framework
- SQLite (for local development)
- Other third-party libraries such as Folium, GeoPandas, and Django REST Framework GIS for mapping and spatial data
- A third-party API key for data processing and validation

## Setup Instructions

1. `git clone https://github.com/TechnoServe/TerraTrac-Validation-Portal.git`
2. `cd TerraTrac-Validation-Portal`
3. `python3 -m venv venv`
4. `source venv/bin/activate` # On Windows use \`venv\\Scripts\\activate\`
5. `pip install -r requirements.txt`

### Update the DATABASES section in eudr_backend/settings.py to match your local or production database setup (PostgreSQL or SQLite)

   `python manage.py migrate`

### Create a .env file in the project root and add your environment variables

   `AGSTACK_API_EMAIL=`
   `AGSTACK_API_PASSWORD=`
   `EMAIL_HOST_USER=`
   `EMAIL_HOST_PASSWORD=`
   `EMAIL_HOST_DEFAULT_USER=`
   `AWS_ACCESS_KEY_ID=`
   `AWS_SECRET_ACCESS_KEY=`
   `AWS_STORAGE_BUCKET_NAME=`
   `AWS_S3_REGION_NAME=`

### Run the development server

   `python manage.py runserver`

## API Documentation

The app provides a RESTful API for collecting, processing, and retrieving data.

- **Upload Data**:

  - Endpoint: /api/farm/add/
  - Method: POST

- **Get Processed Data**:

  - Endpoint: /api/farm/list/
  - Method: GET
  - Response: JSON of processed farm data

## Running Tests

To run the tests:

`python manage.py test`

## Deployment

1. Ensure you have set the environment variables in your hosting environment
2. `python manage.py migrate`
3. `python manage.py collectstatic`
4. Deploy the application using your preferred method (Heroku, AWS, DigitalOcean, etc.).

## Contributing

We welcome contributions from the community! Please read our [Contributing Guidelines](./CONTRIBUTING.md) to get started. This document will help you understand how to set up your local environment, submit code changes, and follow our coding standards.

Thank you for helping improve our project!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
