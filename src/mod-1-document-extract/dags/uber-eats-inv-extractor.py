from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.utils.dates import days_ago
from datetime import datetime
import os

# New in Airflow 3.0: LLM Task API
from airflow.decorators import task

@dag(
    dag_id="invoice_extraction_dag",
    schedule="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["invoices", "minio", "llm", "postgres"]
)
def invoice_extraction_pipeline():

    # 1. Download PDF from MinIO (S3-compatible)
    @task()
    def download_invoice_from_minio(bucket_name: str, key: str) -> str:
        """Download invoice PDF from MinIO and return local file path."""
        s3 = S3Hook(aws_conn_id="minio_default")  # use your MinIO connection
        local_path = f"/tmp/{os.path.basename(key)}"
        s3.download_file(bucket_name=bucket_name, key=key, local_path=local_path)
        return local_path

    # 2. Extract data using OpenAI LLM
    @task.llm(
        conn_id="openai_default",  # use your OpenAI connection
        model="gpt-4o-mini",       # lightweight + accurate for PDFs
        prompt_template="""
        You are an expert invoice parser. From the following UberEats invoice PDF, extract:
        - Restaurant name
        - CNPJ
        - Address
        - Date & time
        - List of items: name, quantity, unit price
        - Subtotal
        - Taxes & fees
        - Total
        - Payment method
        Return JSON format.
        """
    )
    def extract_invoice_data(file_path: str) -> dict:
        """Extract structured invoice data using OpenAI."""
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        return pdf_bytes  # @task.llm handles passing file content

    # 3. Store structured data in Postgres
    @task()
    def store_to_postgres(invoice_data: dict):
        """Insert extracted data into invoice_db (Postgres)."""
        pg_hook = PostgresHook(postgres_conn_id="invoice_db")
        conn = pg_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invoices (restaurant, cnpj, address, items, subtotal, taxes, total, payment_method, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            invoice_data["restaurante"],
            invoice_data["cnpj"],
            invoice_data["endereco"],
            str(invoice_data["itens"]),
            invoice_data["subtotal"],
            invoice_data["taxas"],
            invoice_data["total"],
            invoice_data["pagamento"],
            datetime.now()
        ))
        conn.commit()
        cursor.close()
        conn.close()

    # Workflow orchestration
    local_pdf = download_invoice_from_minio("invoices-bucket", "uber/inv-mod-3-06.pdf")
    extracted_data = extract_invoice_data(local_pdf)
    store_to_postgres(extracted_data)

invoice_extraction_pipeline()
