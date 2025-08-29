import psycopg

conn_string = 'postgresql://neondb_owner:npg_41AChMzNocxw@ep-bold-king-a8mmlufn-pooler.eastus2.azure.neon.tech/neondb?sslmode=require'

conn = psycopg.connect(conn_string)
print("Connection established")
cursor = conn.cursor()