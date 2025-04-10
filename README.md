
# Time Conversion Assistant

A Streamlit-based web application that helps users with time-related queries and conversions using Amazon Bedrock.

## Prerequisites

- Python 3.8 or higher
- Podman installed and configured
- Access to Amazon Bedrock
- Valid AWS credentials configured

## Installation

1. Create and activate a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# For Windows
venv\Scripts\activate
# For macOS/Linux
source venv/bin/activate

2. pip install -r requirements.txt

3. streamlit run ui.py

4. The application will start and open in your default web browser, typically at http://localhost:8501

5. And any other dependencies your application needs. You can create a requirements.txt file by running:
```bash
pip freeze > requirements.txt
