import psycopg2


# DatabaseUtil class with try-except block to handle connection errors
class DatabaseUtil:

    def __init__(self, db_config):
        self.db_config = db_config

        # try block will try to connect to the database
        try:                                                    
            self.connection = psycopg2.connect(**db_config)

        # except block to handle connection errors if any occur during the try block
        except Exception as e:      
            print(f"Error connecting to database: {e}")
            self.connection = None

    def schema_details(self, schema_name):          

        # schema_info_context will store the schema information
        schema_info_context = ""

        # cursor will be used to execute SQL queries
        connection = self.connection
        cursor = connection.cursor()

        schema_info_context = f"Database Schema: {schema_name}\n"

        try:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s;", (schema_name,))
            table_list = cursor.fetchall()

            # loop through each table in the schema to get table name and column details
            for table in table_list:
                table_name = table[0]
                schema_info_context = f"{schema_info_context}\nTable: {table_name}\n"

                # Adding column details and data types
                cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s;",(table_name,))
                column_list = cursor.fetchall()

                # loop through each column in the table to get column name and data type
                for column in column_list:
                    column_name = column[0]
                    data_type = column[1]
                    schema_info_context = f"{schema_info_context}\nColumn: {column_name}\nData Type: {data_type}\n"

                # Adding sample data so the agent can understand the table structure
                cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
                sample_data = cursor.fetchall()
                schema_info_context = f"{schema_info_context}\nSample Data:\n{sample_data}\n"
                for row in sample_data:
                    schema_info_context = f"{schema_info_context}\n{row}\n"
        except Exception as e:
            print(f"Error getting schema details: {e}")
            schema_info_context = f"Error getting schema details: {e}"
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        return schema_info_context
    
    def execute_sql(self, sql_query):
        try:
            connection = self.connection
            cursor = connection.cursor()
            cursor.execute(sql_query)
            result = cursor.fetchall()
            connection.commit()
            return str(result)
        except Exception as e:
            print(f"Error executing SQL query: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:            
                connection.close()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    obj = DatabaseUtil({
        "host": os.environ["host"],
        "port": int(os.environ["port"]),
        "database": os.environ["database"],
        "user": os.environ["user"],
        "password": os.environ["password"],
    })
    print(obj.schema_details("public"))
        