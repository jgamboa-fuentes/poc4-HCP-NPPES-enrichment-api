# modules/db_handler.py
import os
import pyodbc

def get_db_connection():
    """Establishes a connection to the Azure Synapse database."""
    conn_str = (
        f"DRIVER={os.environ['DB_DRIVER']};"
        f"SERVER={os.environ['DB_SERVER']};"
        f"DATABASE={os.environ['DB_NAME']};"
        f"UID={os.environ['DB_USER']};"
        f"PWD={os.environ['DB_PASSWORD']};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

def get_npis_to_enrich(cursor, source_table: str) -> list:
    """
    Finds all rows in the source table that have at least one empty field
    and returns their NPIs. This replaces the VBA 'RowNeedsEnrichment' check.
    """
    query = f"""
        SELECT TargetList_HCP_NPI_ID
        FROM {source_table}
        WHERE TargetList_HCP_NPI_ID IS NOT NULL AND (
            TargetList_FirstName IS NULL OR
            TargetList_LastName IS NULL OR
            TargetList_PrimarySpecialty IS NULL OR
            TargetList_ContactType IS NULL OR
            TargetList_AddressLine1 IS NULL OR
            TargetList_City IS NULL OR
            TargetList_State IS NULL OR
            TargetList_ZIP IS NULL
        )
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    return [row[0] for row in rows]

def update_hcp_record(cursor, destination_table: str, npi: str, data: dict):
    """
    Updates a record in the destination table, filling only the empty fields.
    This uses COALESCE to replace the VBA 'FillIfEmpty' logic efficiently.
    """
    # Map dictionary keys to table column names
    field_map = {
        "first_name": "TargetList_FirstName",
        "middle_name": "TargetList_MiddleName",
        "last_name": "TargetList_LastName",
        "primary_specialty": "TargetList_PrimarySpecialty",
        "contact_type": "TargetList_ContactType",
        "addr1": "TargetList_AddressLine1",
        "addr2": "TargetList_AddressLine2",
        "city": "TargetList_City",
        "state": "TargetList_State",
        "zip": "TargetList_ZIP"
    }
    
    # Prepare the SET clauses and parameters for the SQL query
    set_clauses = []
    params = []
    for key, value in data.items():
        if key in field_map and value is not None:
            # COALESCE fills the column only if it's currently NULL
            set_clauses.append(f"{field_map[key]} = COALESCE({field_map[key]}, ?)")
            params.append(str(value)) # Ensure all params are strings or compatible types

    if not set_clauses:
        return # Nothing to update
    
    params.append(npi) # Add the NPI for the WHERE clause
    
    query = f"""
        UPDATE {destination_table}
        SET {', '.join(set_clauses)}
        WHERE TargetList_HCP_NPI_ID = ?
    """
    
    try:
        cursor.execute(query, params)
    except Exception as e:
        print(f"Failed to update record for NPI {npi}: {e}")