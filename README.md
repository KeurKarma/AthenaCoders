# SQL Query Interface Flask Application

This Flask application provides a web interface to execute SQL queries directly or by converting natural language questions into SQL queries using an external NLP API.

## Features

- **Direct SQL Execution**: Enter and run SQL queries against a pre-configured SQL Server database.
- **Natural Language to SQL**: Input a question in plain English, which is sent to an NLP API to generate a SQL query. The generated query is then executed.
- **Results Display**: Query results are displayed in a table on the web page.
- **Interactive Table**:
  - Each row in the results table has a "Details" button that logs the row's data to the browser console.
  - A common "Information Request" button in the table header logs all current results to the console.
  - The "Actions" column containing these buttons is sticky and remains visible during horizontal scrolling.
- **Basic Security**: Includes some basic checks to prevent common SQL injection patterns and multiple statement execution. **Note**: This is not exhaustive and should be improved for production environments.

## Project Structure

```
.
├── static/
│   └── style.css         # CSS styles for the application
├── templates/
│   └── index.html        # HTML template for the web interface
├── api_config.py         # Configuration for the NLP API (Bearer Token, URL, Workflow ID)
├── app.py                # Main Flask application logic
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Prerequisites

- Python 3.x
- Access to a SQL Server instance.
- Credentials and endpoint for an NLP API capable of converting natural language to SQL.

## Setup

1. **Clone the repository (if applicable) or ensure all project files are in a single directory.**
2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Database Connection:**
   Open `app.py` and update the `CONN_STR` variable with your SQL Server connection details:

   ```python
   CONN_STR = (
       "DRIVER={SQL Server};"
       "Server=YOUR_SERVER_NAME_OR_IP;"  # e.g., localhost, TR-FJH5JX3
       "Database=YOUR_DATABASE_NAME;"    # e.g., TaxyWin
       "UID=YOUR_USERNAME;"              # e.g., sa
       "PWD=YOUR_PASSWORD;"              # e.g., p@ssw0rd
       "Trusted_Connection=no;"          # Or 'yes' if using Windows Authentication
   )
   ```

   Ensure you have the necessary SQL Server ODBC drivers installed on your system.
4. **Configure NLP API:**
   Create a file named `api_config.py` in the root of the project directory with the following content, replacing the placeholder values with your actual NLP API credentials and endpoint:

   ```python
   # api_config.py
   BEARER_TOKEN = "YOUR_NLP_API_BEARER_TOKEN"
   NLP_API_URL = "YOUR_NLP_API_ENDPOINT_URL"
   WORKFLOW_ID = "YOUR_NLP_API_WORKFLOW_ID" # Or any other identifier your API might need
   ```

## Running the Application

1. **Ensure your virtual environment is activated.**
2. **Navigate to the project's root directory in your terminal.**
3. **Run the Flask application:**
   ```bash
   python app.py
   ```
4. **Open your web browser and go to:** `http://127.0.0.1:5000/`

## Usage

- The interface defaults to "SQL Query Mode". You can type your SQL query in the textarea and click "Execute Query".
- To use the natural language feature, toggle the switch to "Natural Language Query Mode". Type your question and click "Get & Execute SQL". The generated SQL will be displayed below the results table.
- Results from the query will appear in the table.
- Use the "Details" button on any row or the "Information Request" button in the header to log data to your browser's developer console.

## Important Security Note

The SQL injection prevention in this application is very basic and intended for demonstration purposes only. For a production environment, you **must** implement more robust security measures, such as:

- Using parameterized queries (e.g., with `cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`).
- Employing an Object-Relational Mapper (ORM) like SQLAlchemy.
- Thorough input validation and sanitization on both client and server sides.
- Implementing proper access controls and database user permissions.
