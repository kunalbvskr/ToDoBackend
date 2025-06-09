import pyodbc
import uvicorn
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()
max_retries = 10
retry_interval = 3

# update your database name and connection strings
db_name = "kbvskrdb"        

server_connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:kbvskr-mssqlserver.database.windows.net,1433;Uid=dbadmin;Pwd=Kbvskr@12345;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

db_connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:kbvskr-mssqlserver.database.windows.net,1433;Database=kbvskrdb;Uid=dbadmin;Pwd=Kbvskr@12345;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# server_connection_string = (
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=kbvskr-mssqlserver.database.windows.net;"
#     "UID=sa;"
#     "PWD=Kbvskr@12345;"
# )

# db_connection_string = (
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=kbvskr-mssqlserver.database.windows.net;"
#     f"DATABASE={db_name};"
#     "UID=sa;"
#     "PWD=Kbvskr@12345;"
# )

app = FastAPI()

# Configure CORSMiddleware to allow all origins (disable CORS for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all origins (use '*' for development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the Task model
class Task(BaseModel):
    title: str
    description: str

# Create a table for tasks (You can run this once outside of the app)
# @app.get("/api")
@app.on_event("startup")
def create_tasks_table():
    print(f"⏳ Creating {db_name} database..")
    try:
        #Connect without db to create it
        with pyodbc.connect(server_connection_string, autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"IF DB_ID('{db_name}') IS NULL CREATE DATABASE {db_name}")

        for attempt in range(max_retries):
            try:
                with pyodbc.connect(db_connection_string, autocommit=True) as conn:
                    print(f"✅ Database {db_name} is now created.")
                    break
            except pyodbc.OperationalError as e:
                print(f"⏳ Waiting for DB to be ready... Attempt {attempt + 1}")
                time.sleep(retry_interval)
        else:
            raise Exception("❌ Database not accessible after multiple retries.")

        # Connect to DB and create table
        with pyodbc.connect(db_connection_string, autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                IF OBJECT_ID('Tasks', 'U') IS NULL
                CREATE TABLE Tasks (
                    ID int NOT NULL PRIMARY KEY IDENTITY,
                    Title varchar(255),
                    Description text
                );
            """)
            print("✅ DB table is created. Tasks API is ready.")
    except Exception as e:
        print(e)

# List all tasks
@app.get("/api")
def get_tasks():
    tasks = []
    with pyodbc.connect(db_connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks")
        for row in cursor.fetchall():
            task = {
                "ID": row.ID,
                "Title": row.Title,
                "Description": row.Description
            }
            tasks.append(task)
    return tasks

# List all tasks
@app.get("/api/tasks")
def get_tasks():
    tasks = []
    with pyodbc.connect(db_connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks")
        for row in cursor.fetchall():
            task = {
                "ID": row.ID,
                "Title": row.Title,
                "Description": row.Description
            }
            tasks.append(task)
    return tasks

# Retrieve a single task by ID
@app.get("/api/tasks/{task_id}")
def get_task(task_id: int):
    with pyodbc.connect(db_connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks WHERE ID = ?", task_id)
        row = cursor.fetchone()
        if row:
            task = {
                "ID": row.ID,
                "Title": row.Title,
                "Description": row.Description
            }
            return task
        return {"message": "Task not found"}

# Create a new task
@app.post("/api/tasks")
def create_task(task: Task):
    with pyodbc.connect(db_connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Tasks (Title, Description) VALUES (?, ?)", task.title, task.description)
        conn.commit()
    return task

# Update an existing task by ID
@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated_task: Task):
    with pyodbc.connect(db_connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Tasks SET Title = ?, Description = ? WHERE ID = ?", updated_task.title, updated_task.description, task_id)
        conn.commit()
        return {"message": "Task updated"}

# Delete a task by ID
@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    with pyodbc.connect(db_connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Tasks WHERE ID = ?", task_id)
        conn.commit()
        return {"message": "Task deleted"}

if __name__ == "__main__":
    create_tasks_table()
    uvicorn.run(app, host="0.0.0.0", port=8000)
