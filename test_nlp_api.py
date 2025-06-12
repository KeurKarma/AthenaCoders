import requests
import json
import api_config # Your API configuration file

# --- Configuration ---
# You can change this query for testing different natural language inputs
NATURAL_LANGUAGE_QUERY = "Give all clients which has turnover is more than 1000" 
# --- End Configuration ---

def test_nlp_api(nlp_query):
    """
    Sends a query to the NLP-to-SQL API and prints the response.
    """
    if api_config.BEARER_TOKEN == "YOUR_BEARER_TOKEN_HERE":
        print("ERROR: Please update api_config.py with your actual BEARER_TOKEN.")
        return

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_config.BEARER_TOKEN}'
    }
    payload = {
        "workflow_id": api_config.WORKFLOW_ID,
        "query": nlp_query,
        "is_persistence_allowed": True  # As per your curl example
    }

    print(f"Sending query to NLP API: {api_config.NLP_API_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")

    try:
        response = requests.post(api_config.NLP_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        
        print("NLP API Response (Status Code: {}):\n".format(response.status_code))
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
            
            # Attempt to extract the SQL query based on the logic in app.py
            # This is for demonstration and might need adjustment based on actual response
            generated_sql_query = None
            if response_json.get("response") and isinstance(response_json["response"], list) and len(response_json["response"]) > 0:
                first_response_item = response_json["response"][0]
                if first_response_item.get("sql_query_results") and \
                   isinstance(first_response_item["sql_query_results"], list) and \
                   len(first_response_item["sql_query_results"]) > 0:
                    generated_sql_query = first_response_item["sql_query_results"][0].get("sql")
            
            if not generated_sql_query: # Fallback or simpler structure
                 if isinstance(response_json.get("sql"), str) : 
                    generated_sql_query = response_json.get("sql")
                 elif isinstance(response_json.get("query"), str) : 
                    generated_sql_query = response_json.get("query")
                 elif isinstance(response_json.get("sql_query"), str) : 
                    generated_sql_query = response_json.get("sql_query")

            if generated_sql_query:
                print(f"\n--- Extracted SQL Query (for verification) ---\n{generated_sql_query}")
            else:
                print("\n--- Could not automatically extract SQL query from this response structure. ---")

        except json.JSONDecodeError:
            print("Response was not valid JSON:")
            print(response.text)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Error connecting to NLP API: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    print("--- Testing NLP-to-SQL API ---")
    test_nlp_api(NATURAL_LANGUAGE_QUERY)
    print("\n--- Test Complete ---")
