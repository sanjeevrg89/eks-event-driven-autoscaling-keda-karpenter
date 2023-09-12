
from flask import Flask, render_template, request, redirect, url_for
import boto3
import json
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Initialize SQS and EventBridge clients
sqs = boto3.client('sqs', region_name='us-west-2')
eventbridge = boto3.client('events', region_name='us-west-2')

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('Concerts')

# SQS Queue URL
queue_url = 'https://sqs.us-west-2.amazonaws.com/123255318457/TicketQueue'

def get_concerts_from_dynamodb():
    try:
        # Fetch all concerts from DynamoDB
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        logging.error(f"An error occurred while fetching concerts: {e}")
        return []

@app.route('/')
def index():
    concerts = get_concerts_from_dynamodb()
    return render_template('index.html', concerts=concerts)

@app.route('/buy/<int:concert_id>', methods=['POST'])
def buy(concert_id):
    try:
        # Find the concert in DynamoDB and reduce tickets
        response = table.get_item(Key={'id': concert_id})
        concert = response.get('Item')
        if concert and concert['tickets'] > 0:
            new_tickets = concert['tickets'] - 1
            table.update_item(
                Key={'id': concert_id},
                UpdateExpression='set tickets=:t',
                ExpressionAttributeValues={':t': new_tickets},
                ConditionExpression='tickets > :zero',
                ExpressionAttributeValues={':zero': 0}
            )

            # Send event to SQS
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({
                    'event_type': 'ticket_purchased',
                    'concert_id': concert_id
                })
            )

        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"An error occurred while buying a ticket: {e}")
        return redirect(url_for('index'))

@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    try:
        # Validate the input
        concert_id = int(request.form.get('concert_id'))
        new_inventory = int(request.form.get('new_inventory'))
        if new_inventory < 0:
            logging.warning("Inventory cannot be negative")
            return redirect(url_for('index'))

        # Code to update inventory in DynamoDB
        table.update_item(
            Key={'id': concert_id},
            UpdateExpression='set tickets=:t',
            ExpressionAttributeValues={':t': new_inventory}
        )

        # Send event to EventBridge
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'com.mycompany.concerts',
                    'DetailType': 'inventory_updated',
                    'Detail': json.dumps({
                        'concert_id': concert_id,
                        'new_inventory': new_inventory
                    }),
                    'Resources': ['resource1', 'resource2']
                }
            ]
        )

        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"An error occurred while updating inventory: {e}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
