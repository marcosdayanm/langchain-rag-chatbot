import psycopg2
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

logging.basicConfig(filename='app.log', level=logging.INFO)
load_dotenv()

POSTGRES_URL = os.getenv("POSTGRES_URL")

def get_db_connection():
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        return conn
    except psycopg2.Error as e:
        logging.error(f"Error connecting to database: {e}")
        raise

def create_application_logs():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS application_logs (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT,
                    user_query TEXT,
                    gpt_response TEXT,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except psycopg2.Error as e:
        logging.error(f"Error creating application_logs: {e}")
        conn.rollback()
    finally:
        conn.close()

def insert_application_logs(session_id, user_query, gpt_response, model):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO application_logs (session_id, user_query, gpt_response, model)
                VALUES (%s, %s, %s, %s)
            ''', (session_id, user_query, gpt_response, model))
            conn.commit()
    except psycopg2.Error as e:
        logging.error(f"Error inserting in application_logs: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_chat_history(session_id):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('''
                SELECT user_query, gpt_response
                FROM application_logs
                WHERE session_id = %s
                ORDER BY created_at
            ''', (session_id,))
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                messages.extend([
                    HumanMessage(content=row['user_query']),
                    AIMessage(content=row['gpt_response'])
                ])
            logging.info(f"Retrieved chat history for session {session_id}: {messages}")
            return messages
    except psycopg2.Error as e:
        logging.error(f"Error retrieving chat history: {e}")
        return []
    finally:
        conn.close()

def create_document_store():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS document_store (
                    id SERIAL PRIMARY KEY,
                    filename TEXT,
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except psycopg2.Error as e:
        logging.error(f"Error creating document_store: {e}")
        conn.rollback()
    finally:
        conn.close()

def insert_document_record(filename):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('''
                INSERT INTO document_store (filename)
                VALUES (%s)
                RETURNING id
            ''', (filename,))
            file_id = cursor.fetchone()['id']
            conn.commit()
            return file_id
    except psycopg2.Error as e:
        logging.error(f"Error inserting in document_store: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def delete_document_record(file_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                DELETE FROM document_store
                WHERE id = %s
            ''', (file_id,))
            conn.commit()
            return True
    except psycopg2.Error as e:
        logging.error(f"Error deleting from document_store: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_documents():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('''
                SELECT id, filename, upload_timestamp
                FROM document_store
                ORDER BY upload_timestamp DESC
            ''')
            rows = cursor.fetchall()
            return [dict(doc) for doc in rows]
    except psycopg2.Error as e:
        logging.error(f"Error getting all the documents: {e}")
        return []
    finally:
        conn.close()

create_application_logs()
create_document_store()
