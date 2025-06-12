from flask import Flask, request, jsonify, render_template
import requests
import api_config
import pyodbc

def getat():
    natural_language_query = "show me any one clients"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_config.BEARER_TOKEN}'
    }
    
    payload = {
        "workflow_id": api_config.WORKFLOW_ID,
        "query": natural_language_query,
        "is_persistence_allowed": True
    }

    nlp_response = requests.post(api_config.NLP_API_URL, headers=headers, json=payload)
    nlp_response.raise_for_status()
    nlp_data = nlp_response.json()
    generated_sql_query = None
    try:
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
    
    except (KeyError, IndexError, TypeError) as e:
        return jsonify({"error": f"Could not parse SQL query from NLP API response. Structure might be unexpected. Error: {str(e)}", "nlp_response": nlp_data}), 500
        
    if not generated_sql_query:
        return jsonify({"error": "NLP API did not return a SQL query or it could not be extracted.", "nlp_response": nlp_data}), 500

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
    return db_query_result
    if db_query_result["error"]:
            return jsonify({"error": db_query_result["error"], "generated_sql": generated_sql_query}), 500
        
    return jsonify({
        "results": db_query_result["results"], 
        "columns": db_query_result["columns"],
        "generated_sql": generated_sql_query # Also return the SQL that was run
    })           

def execute_query_db(query_string):
    CONN_STR = (
    "DRIVER={SQL Server};"
    "Server=TR-FJH5JX3;"
    "Database=TaxyWin;"
    "UID=sa;"
    "PWD=p@ssw0rd;"
    "Trusted_Connection=no;"
    )
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

if __name__ == "__main__":
    try:
        response_data = getat()
        print(response_data)
    except Exception as e:
        print(f"Error: {str(e)}")