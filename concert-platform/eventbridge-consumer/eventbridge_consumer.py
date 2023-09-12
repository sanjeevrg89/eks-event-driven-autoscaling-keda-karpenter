
import boto3
import json
import datetime
import time

# Initialize SQS client
sqs = boto3.client('sqs', region_name='us-west-2')
queue_url = 'https://sqs.us-west-2.amazonaws.com/123255318457/ConsumerQueue'

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('InventoryRecords')

def consume_eventbridge_events():
    while True:
        try:
            # Long Polling: Set WaitTimeSeconds to a value greater than 0 (e.g., 10 seconds)
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            
            messages = response.get('Messages')
            
            if messages:
                for message in messages:
                    # Rate Limiting: Sleep for a short duration (e.g., 0.1 seconds) to control the rate
                    time.sleep(0.1)
                    
                    event = json.loads(message['Body'])
                    
                    # Event Filtering: If different event types are expected, filter based on attributes
                    if 'event_type' in event and event['event_type'] == 'inventory_updated':
                        process_inventory_event(event)
                        
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)  # Sleep for a bit before retrying

def process_inventory_event(event):
    try:
        # Extracting relevant information from the event
        concert_id = event.get('concert_id')
        new_inventory = event.get('new_inventory')

        # Current timestamp for the inventory update
        timestamp = str(datetime.datetime.now())

        # Update the inventory record in DynamoDB
        response = table.put_item(
            Item={
                'concert_id': concert_id,
                'new_inventory': new_inventory,
                'timestamp': timestamp
            }
        )
        
        # Check if the record was successfully inserted
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"Successfully processed inventory event for concert ID: {concert_id}")
        else:
            print(f"Failed to process inventory event for concert ID: {concert_id}")
    except Exception as e:
        print(f"An error occurred while processing the event: {e}")

if __name__ == "__main__":
    consume_eventbridge_events()