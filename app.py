import pyodbc
from flask import Flask, request, jsonify, render_template
import requests # For making HTTP requests to the NLP API
import api_config # Import the new configuration file
import json # For JSONDecodeError

app = Flask(__name__)

# Define the connection string
CONN_STR = (
    "DRIVER={SQL Server};"
    "Server=TR-FJH5JX3;"
    "Database=TaxyWin;"
    "UID=sa;"
    "PWD=p@ssw0rd;"
    "Trusted_Connection=no;"
)

def execute_query_db(query_string):
    """Connects to the database, executes a query, and returns results."""
    conn = None  # Initialize conn to None
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute(query_string)
        
        columns = [column[0] for column in cursor.description]
        results = []
        rows = cursor.fetchall()
        for row in rows:
            # Convert pyodbc.Row to list and decode bytes to strings
            processed_row = []
            for cell in row:
                if isinstance(cell, bytes):
                    processed_row.append(cell.decode('utf-8', errors='replace')) # Decode bytes to string
                else:
                    processed_row.append(cell)
            results.append(processed_row)
            
        cursor.close()
        return {"columns": columns, "results": results, "error": None}
    except pyodbc.Error as e:
        return {"columns": [], "results": [], "error": str(e)}
    except Exception as e:
        return {"columns": [], "results": [], "error": f"An unexpected error occurred: {str(e)}"}
    finally:
        if conn:
            conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def handle_query():
    try:
        data = request.get_json()
        query = data.get('query')

        if not query:
            return jsonify({"error": "No query provided"}), 400

        # Basic validation: prevent very common SQL injection attempts (this is NOT exhaustive)
        # For a production system, use parameterized queries or a more robust ORM/sanitization.
        disallowed_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "CREATE", "ALTER", ";--", "/*", "*/"]
        for keyword in disallowed_keywords:
            if keyword.lower() in query.lower():
                # Check for common comment-out patterns that might bypass simple checks
                if query.lower().count(keyword.lower()) > query.lower().count(f"'{keyword.lower()}'") and \
                   query.lower().count(keyword.lower()) > query.lower().count(f"\"{keyword.lower()}\""):
                    return jsonify({"error": f"Query contains potentially harmful keyword: {keyword}"}), 403
        
        # Further check for execution of multiple statements if not allowed
        if ';' in query and query.strip().lower() != "select 1;": # Allow simple test like "select 1;"
            # Count semicolons not within string literals
            in_single_quote = False
            in_double_quote = False
            semicolon_count = 0
            for char in query:
                if char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif char == ';' and not in_single_quote and not in_double_quote:
                    semicolon_count += 1
            
            if semicolon_count > 1 or (semicolon_count == 1 and not query.strip().endswith(';')):
                 return jsonify({"error": "Multiple SQL statements or unsafe query structure detected."}), 403


        query_result = execute_query_db(query)
        
        if query_result["error"]:
            return jsonify({"error": query_result["error"]}), 500
        
        return jsonify({"results": query_result["results"], "columns": query_result["columns"]})

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/nlp_to_sql_query', methods=['POST'])
def handle_nlp_query():
    try:
        data = request.get_json()
        natural_language_query = data.get('nlp_query')

        if not natural_language_query:
            return jsonify({"error": "No natural language query provided"}), 400

        # Prepare to call the NLP API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_config.BEARER_TOKEN}'
        }
        payload = {
            "workflow_id": api_config.WORKFLOW_ID,
            "query": natural_language_query,
            "is_persistence_allowed": True
        }
        app.logger.info(f"Calling NLP API. URL: {api_config.NLP_API_URL}, Headers: {headers}, Payload: {payload}")

        # Call the NLP API
        nlp_response = requests.post(api_config.NLP_API_URL, headers=headers, json=payload)
        app.logger.info(f"NLP API Response Status Code: {nlp_response.status_code}")
        app.logger.info(f"NLP API Response Headers: {nlp_response.headers}")
        # Log the first 500 characters of the response text to avoid overly long logs
        response_text_preview = nlp_response.text[:500]
        app.logger.info(f"NLP API Response Text (Preview): {response_text_preview}...")

        nlp_response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        
        nlp_data = nlp_response.json()
        app.logger.info(f"NLP API Response JSON (parsed): {nlp_data}")

        # Assuming the NLP API returns JSON with a field like 'sql_query' or similar
        # Adjust this based on the actual response structure of your NLP API
        # For example, if the SQL is nested: nlp_data.get('result', {}).get('sql_query')
        # Based on typical API responses, it might be in a 'data' or 'result' field.
        # Let's assume a simple structure for now:
        # { "response": [ { "sql": "SELECT ..." } ] } or similar.
        # You will need to inspect the actual NLP API response to get the correct path.
        
        # --- Placeholder for extracting SQL query ---
        # This part is CRITICAL and depends on the exact structure of the NLP API's JSON response.
        # For demonstration, let's assume the response is:
        # { "response": [ { "sql_query_results": [ { "sql": "SELECT ..." } ] } ] }
        # You MUST update this extraction logic based on the actual API response.
        generated_sql_query = None
        try:
            # Extract SQL query from the new structure: result.answer["anthropic.claude-v3.7-sonnet"]
            raw_sql_from_api = nlp_data.get("result", {}).get("answer", {}).get("anthropic.claude-v3.7-sonnet")

            if raw_sql_from_api and isinstance(raw_sql_from_api, str):
                # Remove markdown formatting (```sql ... ```)
                if raw_sql_from_api.startswith("```sql\n"):
                    generated_sql_query = raw_sql_from_api[len("```sql\n"):]
                elif raw_sql_from_api.startswith("```"): # More generic ``` removal
                    generated_sql_query = raw_sql_from_api[3:]
                else:
                    generated_sql_query = raw_sql_from_api # Assume no markdown if specific prefix not found

                if generated_sql_query.endswith("\n```"):
                    generated_sql_query = generated_sql_query[:-len("\n```")]
                elif generated_sql_query.endswith("```"): # More generic ``` removal
                    generated_sql_query = generated_sql_query[:-3]
                
                generated_sql_query = generated_sql_query.strip() # Clean up any leading/trailing whitespace

            else: # Fallback or log if the expected path is not found or not a string
                app.logger.warning(f"Could not find 'anthropic.claude-v3.7-sonnet' in NLP response or it's not a string. NLP Response: {nlp_data}")


        except (KeyError, IndexError, TypeError) as e:
            app.logger.error(f"Error parsing SQL query from NLP API response: {str(e)}. NLP Response: {nlp_data}")
            return jsonify({"error": f"Could not parse SQL query from NLP API response. Structure might be unexpected. Error: {str(e)}", "nlp_response": nlp_data}), 500
        
        if not generated_sql_query:
            app.logger.error(f"NLP API did not return a SQL query or it could not be extracted. NLP Response: {nlp_data}")
            return jsonify({"error": "NLP API did not return a SQL query or it could not be extracted.", "nlp_response": nlp_data}), 500
        # --- End Placeholder ---

        # Validate the generated SQL query (using existing validation)
        disallowed_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "CREATE", "ALTER", ";--", "/*", "*/"]
        for keyword in disallowed_keywords:
            if keyword.lower() in generated_sql_query.lower():
                if generated_sql_query.lower().count(keyword.lower()) > generated_sql_query.lower().count(f"'{keyword.lower()}'") and \
                   generated_sql_query.lower().count(keyword.lower()) > generated_sql_query.lower().count(f"\"{keyword.lower()}\""):
                    return jsonify({"error": f"Generated SQL query contains potentially harmful keyword: {keyword}", "generated_sql": generated_sql_query}), 403
        
        if ';' in generated_sql_query and generated_sql_query.strip().lower() != "select 1;":
            in_single_quote = False
            in_double_quote = False
            semicolon_count = 0
            for char in generated_sql_query:
                if char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif char == ';' and not in_single_quote and not in_double_quote:
                    semicolon_count += 1
            if semicolon_count > 1 or (semicolon_count == 1 and not generated_sql_query.strip().endswith(';')):
                 return jsonify({"error": "Generated SQL query contains multiple statements or unsafe structure.", "generated_sql": generated_sql_query}), 403

        # Execute the generated SQL query
        db_query_result = execute_query_db(generated_sql_query)
        
        if db_query_result["error"]:
            return jsonify({"error": db_query_result["error"], "generated_sql": generated_sql_query}), 500
        
        return jsonify({
            "results": db_query_result["results"], 
            "columns": db_query_result["columns"],
            "generated_sql": generated_sql_query # Also return the SQL that was run
        })

    except requests.exceptions.HTTPError as http_err:
        # Ensure nlp_response is available for logging, even if it's not fully formed JSON
        details_text = "No response details"
        if 'nlp_response' in locals() and hasattr(nlp_response, 'text'):
            details_text = nlp_response.text
        app.logger.error(f"NLP API HTTPError: {str(http_err)}. Response text: {details_text}")
        return jsonify({"error": f"NLP API request failed: {str(http_err)}", "details": details_text}), 500
    except requests.exceptions.RequestException as req_err:
        app.logger.error(f"NLP API RequestException: {str(req_err)}")
        return jsonify({"error": f"Error connecting to NLP API: {str(req_err)}"}), 500
    except json.JSONDecodeError as json_err:
        # This new catch block is specifically for when nlp_response.json() fails
        response_text_for_json_error = "Unknown, response object not available or no text attribute"
        if 'nlp_response' in locals() and hasattr(nlp_response, 'text'):
            response_text_for_json_error = nlp_response.text
        app.logger.error(f"Failed to decode NLP API response as JSON: {str(json_err)}. Response text: {response_text_for_json_error}")
        return jsonify({"error": f"Failed to decode NLP API response as JSON: {str(json_err)}", "details": response_text_for_json_error}), 500
    except Exception as e:
        app.logger.error(f"Unexpected server error during NLP processing: {str(e)}", exc_info=True) # Log full traceback
        return jsonify({"error": f"Server error during NLP processing: {str(e)}"}), 500

# this is just for testing a server
@app.route('/test_route')
def test_route_func():
    app.logger.info("Test route accessed!")
    return "Test route is working!"

if __name__ == '__main__':
    app.run(debug=True)
