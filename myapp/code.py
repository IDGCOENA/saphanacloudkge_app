from langchain_openai import AzureChatOpenAI
from langchain_aws import ChatBedrock
from hdbcli import dbapi
from .key import *
import os
import re

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from hdbcli import dbapi 
from langchain_core.prompts import ChatPromptTemplate

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF
from langchain_core.prompts import PromptTemplate
from typing_extensions import TypedDict, Annotated
from hana_ml import dataframe

#dynamicE2E
import pandas as pd
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET
from langchain_core.prompts import PromptTemplate
from typing_extensions import TypedDict, Annotated
import boto3

"""
Generating triplets and ingesting into HANA Cloud
"""
def store_data(file_path,anthropic,conn):

    #Extract the data from the PDF ,and convert to a graph
    text_documents = PyPDFLoader(file_path).load()
    llm_transformer = LLMGraphTransformer(llm=anthropic)
    graph_documents = llm_transformer.convert_to_graph_documents(text_documents)

    # Define a namespace for the RDF graph
    EX = Namespace("http://example1.org/")

    # Initialize an RDF graph
    g = Graph()

    # Add nodes to the RDF graph
    for document in graph_documents: 
        for node in document.nodes:
            node_uri = URIRef(EX[node.id.replace(" ", "_")])
            g.add((node_uri, RDF.type, EX[node.type.replace(" ", "_")]))

        # Add relationships to the RDF graph
        for relationship in document.relationships:
            source_uri = URIRef(EX[relationship.source.id.replace(" ", "_")])
            target_uri = URIRef(EX[relationship.target.id.replace(" ", "_")])
            g.add((source_uri, EX[relationship.type], target_uri))

    # Extract RDF triples
    rdf_triples = []
    for s, p, o in g:
        rdf_triples.append((str(s), str(p), str(o)))
    
    # Call stored procedure to execute SPARQL query or insert RDF triples
    cursor = conn.cursor()
    try:
        # Iterate through the triples and insert them into the database
        for s, p, o in rdf_triples:
            # Construct a SPARQL INSERT query for each triple
            sparql_insert_query = f"""
                INSERT DATA {{
                    <{s}> <{p}> <{o}> .
                }}
            """

            # Execute the SPARQL query using the stored procedure
            resp = cursor.callproc('SPARQL_EXECUTE', (sparql_insert_query, 'Metadata headers describing Input and/or Output', '?', None))

            # Handle response if necessary
            metadata_headers = resp[3]  # OUT: RQX Response Metadata/Headers
            query_response = resp[2]     # OUT: RQX Response


    finally:
        cursor.close()
    
    print("Triplets uploaded to HANA Cloud")



"""
Set up API and DB credentials
"""
def setup():

    #API Keys and DB Credentials 
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://sap-openaigpt4.openai.azure.com/"
    os.environ["AZURE_OPENAI_API_KEY"] = OPEN_AI_KEY

    #set up LLM 
    openAI = AzureChatOpenAI(
        azure_deployment="gptnew",
        api_version='2023-05-15',
        temperature=1,
        max_tokens=None,
        timeout=None,
        max_retries=2
    )

    os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    anthropic = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")

    conn = dbapi.connect(
        user = HANA_USER,
        password = HANA_PW,
        address = '122ac990-1ac9-4dd0-9f92-94ce5bed0874.hna1.canary-eu10.hanacloud.ondemand.com', #New instance after crash
        port = 443,
    )

    return anthropic,conn

class State(TypedDict):
    question: str
    s: str
    p: str
    o: str
    query: str

#return dictionary where key is query and value is SPARQL query string 
class QueryOutput(TypedDict):
    """Generated SPARQL query."""
    query: Annotated[str, ..., "Syntactically valid SPARQL query."]

def write_query(state: State,anthropic):
    """
    Generate a SPARQL Query, connect to the database, and retrieve the answer to the query
    """
   
    #give example in template and try different LLMs 
    template = '''Given an input question, your task is to create a syntactically correct SPARQL query to retrieve information from an RDF graph. The graph may contain variations in spacing, underscores, dashes, capitalization, reversed relationships, and word order. You must account for these variations using the `REGEX()` function in SPARQL. In the RDF graph, subjects are represented as "s", objects are represented as "o", and predicates are represented as "p". Account for underscores. 

    Example Question: "What are SAP HANA Hotspots Cloud?"
    Example SPARQL Query: SELECT ?s ?p ?o
    WHERE {{
        ?s ?p ?o .
        FILTER(
            REGEX(str(?s), "SAP_HANA_Hotspots_Cloud", "i") ||
            REGEX(str(?o), "SAP_HANA_Hotspots_Cloud", "i")
        )
    }}

    Retrieve only triplets beginning with "<unstructred namespace>" or <strucutured namespace>
    
    Use the following format:
    Question: {input} 
    S: Subject to look for in the RDF graph
    P: Predicate to look for in the RDF graph
    O: Object to look for in the RDF graph
    SPARQL Query: SPARQL Query to run, including s-p-o structure
    '''

    query_prompt_template = PromptTemplate.from_template(template)


    """Generate SPARQL query to fetch information."""
    prompt = query_prompt_template.invoke(
        {
            "input": state["question"],
        }
    )
    structured_llm = anthropic.with_structured_output(QueryOutput)
    result = structured_llm.invoke(prompt)
    print(result["query"])
    return {"query": result["query"]}


def execute_sparql(query_response,conn):
    print()
    cursor = conn.cursor()
    try:
        # Execute 
        resp = cursor.callproc('SPARQL_EXECUTE', (query_response["query"], 'Metadata headers describing Input and/or Output', '?', None))
        
        # Check if the response contains expected OUT parameters
        if resp:
            # Extract metadata and query results from the OUT parameters
            metadata_headers = resp[3]  # OUT: RQX Response Metadata/Headers
            query_response = resp[2]    # OUT: RQX Response
            
            # Handle response
            print("Query Response:", query_response)
            print("Response Metadata:", metadata_headers)
            return query_response
        else:
            print("No response received from stored procedure.")
        
    except Exception as e:
        print("Error executing stored procedure:", e)
    finally:
        cursor.close()

"""
Summarize the information returned by the query
"""
def summarize_info(question, query_response,anthropic): 
    prompt = """Answer the user question below given the following relational information in XML format. Use as much as the query response as possible to give a full, detailed explanation. Interpret the URI and predicate information using context. Don't use phrases like 'the entity identified by the URI,' just say what the entity is. 
    Also make sure the output is readable in a format that can be display through an HTML file, add appropriate formatting.
    Please remove unnecessary information. Do not add information about the triplets. Do not add the source of the data.
    Do not include details about what they are identified as or what kind of entity they are unless asked. Do not add any suggestions unless explicitly asked. Simply give a crisp and direct answer to what has been asked!
    If you do not have an answer, please say so. DO NOT HALLUCINATE!
    User Question: {question}
    Information: {information}
    """
    summarize = PromptTemplate.from_template(prompt)
    prompt_input = summarize.invoke(
            {
                "question": question,
                "information": query_response,
            }
        )

    class QuestionAnswer(TypedDict):
        """Generated SPARQL query."""
        final_answer: Annotated[str, ..., "Answer to user's question."]

    translate_llm = anthropic.with_structured_output(QuestionAnswer)
    return translate_llm.invoke(prompt_input)


#=======================STRUCTURED DATA====================#
def setup_structured():
    
    # set up LLM 
    openAI = AzureChatOpenAI(
        azure_deployment="gptnew",
        api_version='2023-05-15',
        temperature=0.1,  # Lower temperature for more deterministic results
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT        
    )

    
    # Set up AWS credentials
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )
    
    anthropic = ChatBedrock(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"
        
    )

    conn = dbapi.connect(
        user=HANA_ADMIN,
        password=HANA_ADMIN_PW,
        address='122ac990-1ac9-4dd0-9f92-94ce5bed0874.hna1.canary-eu10.hanacloud.ondemand.com',
        port=443,
    )

    return openAI, anthropic, conn

def parse_sparql_results(xml_response: str) -> List[Dict]:
    """Parse SPARQL XML results into a list of dictionaries"""
    try:
        root = ET.fromstring(xml_response)
        results = []
        
        for result in root.findall('.//{http://www.w3.org/2005/sparql-results#}result'):
            row = {}
            for binding in result:
                var_name = binding.attrib['name']
                value = binding[0]  # uri or literal
                if value.tag.endswith('uri'):
                    row[var_name] = value.text
                elif value.tag.endswith('literal'):
                    row[var_name] = value.text
            results.append(row)
        return results
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return []

def extract_metadata(question: str, conn) -> List[Dict]:
    """Extract relevant metadata from RDF triples using SPARQL"""
    cursor = conn.cursor()
    
    try:
        # Execute SPARQL query to get all relevant triples
        sparql_query = """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o.
            FILTER(STRSTARTS(STR(?s), "http://zz.org/"))
        }
        """
        
        resp = cursor.callproc('SPARQL_EXECUTE', (sparql_query, 'Metadata headers describing Input and/or Output', '?', None))
        
        if resp and len(resp) >= 3 and resp[2]:
            # Parse the XML response
            xml_response = resp[2]
            results = parse_sparql_results(xml_response)
            
            # Convert to our standard format
            metadata = []
            for row in results:
                metadata.append({
                    's': row.get('s', ''),
                    'p': row.get('p', ''),
                    'o': row.get('o', '')
                })
            return metadata
        return []
    
    except Exception as e:
        print(f"Error executing SPARQL query: {e}")
        return []
    finally:
        cursor.close()


def analyze_metadata(metadata: List[Dict], question: str, anthropic) -> Dict:
    """Analyze the metadata to identify tables, columns, and relationships"""
    # Convert metadata to a format the LLM can understand
    metadata_str = "\n".join([f"{item['s']} {item['p']} {item['o']}" for item in metadata])
    
    prompt_template = """Given the following RDF metadata about database tables and columns, analyze the user's question and identify:
    1. The main table(s) involved with their schema (SFLIGHT)
    2. The columns needed (including any aggregation functions)
    3. Any filters or conditions
    4. Any joins required

    Important Rules:
    - Always include the schema name (SFLIGHT) before table names
    - When using GROUP BY, include the grouping columns in SELECT
    - Never include any explanatory text in the SQL output
    - For airline codes like American Airlines, use 'AA' in filters

    For each column, include:
    - The column name (prefix with table alias if needed)
    - Any aggregation function (SUM, COUNT, etc.)
    - Any filter conditions
    - Whether it's a grouping column

    For tables, include:
    - The full table name with schema (e.g., SFLIGHT.SBOOK)
    - Any relationships to other tables


    Metadata:
    {metadata}

    Question: {question}

    Return your analysis in this exact format (without any additional explanations):
    Tables: [schema.table]
    Columns: [column names with aggregations like SUM(LOCCURAM)]
    Filters: [filter conditions]
    Joins: [join conditions]
    GroupBy: [columns to group by]
    """
    
    prompt = PromptTemplate.from_template(prompt_template).invoke({
        "metadata": metadata_str,
        "question": question
    })
    
    # We'll use the LLM to extract the key components
    analysis = anthropic.invoke(prompt)
    print("ANTHROPIC!!!!")
    return parse_analysis(analysis.content)

def parse_analysis(analysis_text: str) -> Dict:
    """Parse the LLM's analysis into a structured format"""
    components = {
        "tables": [],
        "columns": [],
        "filters": [],
        "joins": [],
        "group_by": []
    }
    
    # Remove any "Explanation:" text
    analysis_text = analysis_text.split("Explanation:")[0].strip()
    
    # Parse each section
    current_section = None
    for line in analysis_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('Tables:'):
            current_section = 'tables'
            tables = line.split(':')[1].strip()
            components['tables'] = [t.strip() for t in tables.split(',') if t.strip()]
        elif line.startswith('Columns:'):
            current_section = 'columns'
            cols = line.split(':')[1].strip()
            for col_part in cols.split(','):
                col_part = col_part.strip()
                if col_part:
                    if '(' in col_part and ')' in col_part:
                        agg = col_part.split('(')[0].strip().upper()
                        col = col_part.split('(')[1].split(')')[0].strip()
                        components['columns'].append((agg, col))
                    else:
                        components['columns'].append((None, col_part))
        elif line.startswith('Filters:'):
            current_section = 'filters'
            filters = line.split(':')[1].strip()
            components['filters'] = [f.strip() for f in filters.split(' AND ') if f.strip()]
        elif line.startswith('Joins:'):
            current_section = 'joins'
            joins = line.split(':')[1].strip()
            components['joins'] = [j.strip() for j in joins.split(',') if j.strip()]
        elif line.startswith('GroupBy:'):
            current_section = 'group_by'
            group_bys = line.split(':')[1].strip()
            components['group_by'] = [g.strip() for g in group_bys.split(',') if g.strip()]
        elif current_section:
            # Handle multi-line sections
            if current_section == 'tables':
                components['tables'].extend([t.strip() for t in line.split(',') if t.strip()])
            elif current_section == 'columns':
                for col_part in line.split(','):
                    col_part = col_part.strip()
                    if col_part:
                        if '(' in col_part and ')' in col_part:
                            agg = col_part.split('(')[0].strip().upper()
                            col = col_part.split('(')[1].split(')')[0].strip()
                            components['columns'].append((agg, col))
                        else:
                            components['columns'].append((None, col_part))
            elif current_section == 'filters':
                components['filters'].extend([f.strip() for f in line.split(' AND ') if f.strip()])
            elif current_section == 'joins':
                components['joins'].extend([j.strip() for j in line.split(',') if j.strip()])
            elif current_section == 'group_by':
                components['group_by'].extend([g.strip() for g in line.split(',') if g.strip()])
    
    # Ensure schema is included in table names
    components['tables'] = [f"SFLIGHT.{t.split('.')[-1]}" if '.' not in t else t for t in components['tables']]
    
    # Ensure grouping columns are included in SELECT - CORRECTED VERSION
    for group_col in components['group_by']:
        # Check if this exact (None, group_col) pair exists
        col_exists = any(col == (None, group_col) for col in components['columns'])
        # Check if group_col appears in any non-aggregated column reference
        col_part_of_ref = any(group_col in col[1] for col in components['columns'] if col[0] is None)
        
        if not col_exists and not col_part_of_ref:
            components['columns'].append((None, group_col))
    
    return components

def generate_sql(components: Dict) -> str:
    """Generate clean SQL query from the analyzed components"""
    # Validate components
    if not components["tables"]:
        raise ValueError("No tables identified for SQL generation")
    
    # Clean all components first
    def clean_component(component):
        return component.replace('[', '').replace(']', '').strip()
    
    # Build SELECT clause - ensure GROUP BY columns are included
    select_parts = []
    
    # First add all GROUP BY columns to SELECT if they're not already there
    for group_col in components.get("group_by", []):
        group_col = clean_component(group_col)
        if not any(col[1] == group_col for col in components["columns"] if col[0] is None):
            select_parts.append(group_col)
    
    # Then add the requested columns
    for agg, col in components["columns"]:
        col = clean_component(col)
        if not col:
            continue
        if agg:
            select_parts.append(f"{agg}({col}) AS {agg}_{col}")
        else:
            if col not in select_parts:  # Don't add duplicates
                select_parts.append(col)
    
    if not select_parts:  # Default to all columns if none specified
        select_parts.append("*")

    select_clause = ", ".join(select_parts[1:])
    print("SELECT BEFORE "+select_clause)
    print(select_parts)
    
    # Build FROM clause
    from_table = clean_component(components["tables"][0])
    from_clause = from_table
    
    # Add joins only if they exist and are not empty
    join_clauses = []
    for join in components.get("joins", []):
        clean_join = clean_component(join)
        if clean_join and clean_join != 'INNER JOIN':
            join_clauses.append(f"INNER JOIN SFLIGHT.SCUSTOM ON {clean_join}")
    print("INNER JOIN "+clean_join)
    
    # Build WHERE clause
    where_clauses = []
    for filter_cond in components.get("filters", []):
        clean_filter = clean_component(filter_cond)
        if clean_filter:
            where_clauses.append(clean_filter)
    
    where_clause = " AND ".join(where_clauses) if where_clauses else ""
    where_clause = where_clause.replace(",", " AND")
    print("WHERE CLAUSE "+where_clause)
    
    # Build GROUP BY clause
    group_by_columns = [clean_component(g) for g in components.get("group_by", []) if clean_component(g)]
    group_by_clause = ", ".join(group_by_columns) if group_by_columns else ""
    
    # Construct the SQL
    sql = f"SELECT {select_clause} FROM {from_clause}"
    
    if join_clauses:
        sql += " " + " ".join(join_clauses)
    
    if where_clause:
        sql += f" WHERE {where_clause}"
    
    if group_by_clause:
        sql += f" GROUP BY {group_by_clause}"
    
    # Final formatting
    sql = sql.strip()
    if not sql.endswith(';'):
        sql += ';'
    
    return sql

def execute_sql(sql_query: str, conn) -> pd.DataFrame:
    """Execute the generated SQL query and return results"""
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
    except Exception as e:
        print(f"Error executing SQL query: {e}")
        return pd.DataFrame()
    finally:
        cursor.close()

def generate_response_structured(question: str, results: pd.DataFrame, anthropic) -> str:
    """Generate a natural language response from the query results"""
    if results.empty:
        return "No results found for your query."
    
    prompt_template = """Convert the following query results into a natural language response to the user's question. 
    Keep the response concise but informative. Include relevant numbers and comparisons where appropriate.
    
    Question: {question}
    
    Results:
    {results}
    
    Response:
    """
    
    prompt = PromptTemplate.from_template(prompt_template).invoke({
        "question": question,
        "results": results.to_string()
    })
    
    response = anthropic.invoke(prompt)
    return response.content
        
def process_question(question: str, conn, anthropic) -> str:
    """Main function to process a user question with better error handling"""
    try:
        # Step 1: Extract relevant metadata using SPARQL
        metadata = extract_metadata(question, conn)
        
        if not metadata:
            return "Could not retrieve database metadata."
        
        # Step 2: Analyze the metadata and question
        components = analyze_metadata(metadata, question, anthropic)
        
        # Step 3: Generate SQL query
        sql_query = generate_sql(components)
    
        # Step 4: Execute SQL
        results = execute_sql(sql_query, conn)
        
        # Step 5: Generate response
        response = generate_response_structured(question, results, anthropic)
        
        return response
    except Exception as e:
        return f"Error processing question: {str(e)}"