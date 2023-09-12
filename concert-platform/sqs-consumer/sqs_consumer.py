
import boto3
import json
import uuid
import datetime
import logging
import time

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize SQS client
sqs = boto3.client('sqs', region_name='us-west-2')
queue_url = 'https://sqs.us-west-2.amazonaws.com/123255318457/ConsumerQueue'

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('SalesRecords')

def consume_sqs_messages():
    while True:
        try:
            # Long Polling: WaitTimeSeconds set to 10 seconds
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            
            messages = response.get('Messages')
            
            if messages:
                for message in messages:
                    # Rate Limiting: Sleep for 0.1 seconds
                    time.sleep(0.1)
                    
                    event = json.loads(message['Body'])
                    
                    # Event Filtering: Process only 'ticket_purchased' events
                    if 'event_type' in event and event['event_type'] == 'ticket_purchased':
                        process_sales_event(event)
                        
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            time.sleep(5)  # Sleep for a bit before retrying

def process_sales_event(event):
    try:
        # Extracting relevant information from the event
        concert_id = event.get('concert_id')
        
        # Generate a unique ID for the sales record
        sales_id = str(uuid.uuid4())
        
        # Current timestamp for the sale
        timestamp = str(datetime.datetime.now())
        
        # Insert the new sales record into DynamoDB
        response = table.put_item(
            Item={
                'sales_id': sales_id,
                'concert_id': concert_id,
                'timestamp': timestamp
            }
        )
        
        # Check if the record was successfully inserted
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            logging.info(f"Successfully processed sales event for concert ID: {concert_id}")
        else:
            logging.error(f"Failed to process sales event for concert ID: {concert_id}")
    except Exception as e:
        logging.error(f"An error occurred while processing the event: {e}")

if __name__ == "__main__":
    consume_sqs_messages()