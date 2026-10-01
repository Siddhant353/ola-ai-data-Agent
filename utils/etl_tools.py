import os
import requests
import pandas as pd

class ETLTools:
    def __init__(self): #This function will initialize the ETLTools class
        pass

    def extract_load(self,url:str,output_folder:str,format:str="csv"): #This function will extract the data from the database and load it into a pandas dataframe
        """
        This tool will extract the data from the API(url) and loads it  into the desired location(output_folder)
        
        Args:
            url (str): The URL of the API to extract the data from.
            output_folder (str): The folder to load the extracted data into.
        Returns:
            str: A message indicating the success or failure of the extraction and loading process.
        
        """

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # get the project root directory
        output_folder = os.path.join(project_root, output_folder)  # join the output folder with the project root directory

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            filename = os.path.join(output_folder, f"extracted_data.{format}")
            os.makedirs(output_folder, exist_ok=True)

            df = pd.json_normalize(data["results"])
            if format == "csv":
                df.to_csv(filename, index=False)
            elif format == "json":
                df.to_json(filename, orient="records", lines=True)
            elif format == "parquet":
                df.to_parquet(filename, index=False)
            else:
                return f"Unsupported format: {format}"
            
            return f"Extracted data from {url} and loaded it into {filename}"
        except requests.exceptions.RequestException as e:
            return f"Error extracting data from {url}: {e}"


    def transform_load_context(self, file_path:str): #This function will transform the extracted data into a context for the agent
        """
        This tool will transform the extracted data and load it into the desired location(output_folder)
        
        Args:
            file_path (str): The path to the extracted data file.
            output_folder (str): The folder to load the transformed data into.
        Returns:
            str: A message indicating the success or failure of the transformation and loading process.
        """

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":
            df = pd.read_json(file_path)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file extension: {file_extension}"

        top_3_rows = str(df.head(3))

        return top_3_rows

    def execute_code(self, code:str) : #This function will execute the code and return the result
        """
        This tool will execute the code and return the result
        
        Args:
            code (str): The code to execute.
        Returns:
            str: The result of the code execution.
        """
        try:
            exec(code)
            return f"Code executed successfully: {code}"
        except Exception as e:
            return f"Error executing code: {e}"


if __name__ == "__main__":
    obj = ETLTools()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data", "extract", "extracted_data.csv")
    print(obj.transform_load_context(path))

