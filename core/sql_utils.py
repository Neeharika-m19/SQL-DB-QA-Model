# core/sql_utils.py

from sqlalchemy import create_engine, text

def execute_sql_and_format_naturally(db_url: str, sql_query: str) -> str:
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()

            if not rows:
                return "No data found."

            # Format as natural language
            columns = result.keys()
            response_lines = []
            for row in rows:
                row_str = ", ".join(f"{col}: {val}" for col, val in zip(columns, row))
                response_lines.append(row_str)

            return "\n".join(response_lines)

    except Exception as e:
        raise Exception(f"Error executing SQL: {e}")
