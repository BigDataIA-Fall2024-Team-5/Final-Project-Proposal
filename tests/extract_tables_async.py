import boto3
import time
from pprint import pprint


def get_rows_columns_map(table_result, blocks_map):
    rows = {}
    scores = []
    for relationship in table_result['Relationships']:
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map[child_id]
                if cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        rows[row_index] = {}
                    scores.append(str(cell['Confidence']))
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows, scores


def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X '
    return text


def get_textract_results(job_id, aws_access_key, aws_secret_key, aws_region):
    client = boto3.client(
        'textract',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )
    while True:
        response = client.get_document_analysis(JobId=job_id)
        status = response['JobStatus']
        if status in ['SUCCEEDED', 'FAILED']:
            if status == 'FAILED':
                raise Exception("Textract job failed.")
            return response
        print(f"Job status: {status}. Waiting for 5 seconds...")
        time.sleep(5)


def get_table_csv_results(bucket_name, document_name, aws_access_key, aws_secret_key, aws_region):
    client = boto3.client(
        'textract',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    # Start the asynchronous Textract job
    response = client.start_document_analysis(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': document_name
            }
        },
        FeatureTypes=['TABLES']
    )

    job_id = response['JobId']
    print(f"Started Textract job with ID: {job_id}")

    # Wait for the job to complete and fetch results
    result = get_textract_results(job_id, aws_access_key, aws_secret_key, aws_region)

    blocks = result['Blocks']
    pprint(blocks)

    blocks_map = {}
    table_blocks = []
    for block in blocks:
        blocks_map[block['Id']] = block
        if block['BlockType'] == "TABLE":
            table_blocks.append(block)

    if len(table_blocks) <= 0:
        return "NO TABLE FOUND"

    csv = ''
    for index, table in enumerate(table_blocks):
        csv += generate_table_csv(table, blocks_map, index + 1)
        csv += '\n\n'

    return csv


def generate_table_csv(table_result, blocks_map, table_index):
    rows, scores = get_rows_columns_map(table_result, blocks_map)

    table_id = f'Table_{table_index}'
    csv = f'Table: {table_id}\n\n'

    for row_index, cols in rows.items():
        for col_index, text in cols.items():
            csv += f'{text},'
        csv += '\n'

    csv += '\n\n Confidence Scores % (Table Cell) \n'
    cols_count = 0
    for score in scores:
        cols_count += 1
        csv += f'{score},'
        if cols_count == len(cols.items()):
            csv += '\n'
            cols_count = 0

    csv += '\n\n\n'
    return csv


def main():
    bucket_name = 'cfa-publication-data-stores'  # Replace with your S3 bucket name
    document_name = 'Transcript.pdf'  # Replace with your document name
    aws_access_key = ' '  # Replace with your AWS access key
    aws_secret_key = ' '  # Replace with your AWS secret key
    aws_region = 'us-east-2'  # Replace with your AWS region

    table_csv = get_table_csv_results(bucket_name, document_name, aws_access_key, aws_secret_key, aws_region)

    output_file = 'output.csv'
    with open(output_file, "wt") as fout:
        fout.write(table_csv)

    print(f'CSV OUTPUT FILE: {output_file}')


if __name__ == "__main__":
    main()
