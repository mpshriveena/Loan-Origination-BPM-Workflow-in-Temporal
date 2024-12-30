from kafka import KafkaConsumer
import json
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import activity
from activity_workflow import EmailNotificationWorkflow
from datetime import datetime
import temporalio


KAFKA_TOPIC = "loan_disbursement"

async def consume_kafka_message():
    consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=['kafka-1:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='email-workflow-group',
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    client = await Client.connect("temporal:7233")
    
    for message in consumer:
        full_paid = False
        print(f"Received Kafka message: {message.value}")
        kafka_message = message.value
        emailRecipient = kafka_message['email']
        subject = "Monthly Reminder for loan"
        body = f"""
Hello {kafka_message['applicantName']},
    This is just a gentle reminder for your monthly EMI for loan {kafka_message['loanId']}.
    Your loan amount: {kafka_message['loanAmount']}
    Your loan tenure: {kafka_message['loanTenure']}
    Your monthly EMI to be paid: {kafka_message['monthlyEMI']}
    Thank you for choosing us!

Best regards,
Your Loan Team.
            """
        sendDate = str(datetime.now().date())
        email_data =  {
            "emailRecipient": emailRecipient,
            "subject": subject,
            "body": body,
            "sendDate": sendDate
            }
        paid_data = await start_email_cron_workflow(client, email_data, kafka_message['loanId'])

async def start_email_cron_workflow(client, email_data, loanId):
    handle = await client.start_workflow(
        EmailNotificationWorkflow.run,
        email_data,
        id=f"loan-email-workflow{loanId}",
        task_queue="loan-task-queue",
        cron_schedule="* * * * *",
    )
    print(f"Started workflow. Workflow ID: {handle.id}, RunID: {handle.result_run_id}")
    try:
        result = await handle.result()
        print(f"Email Result: {result}")
        return f"Result: {result}"
    except temporalio.client.WorkflowFailureError as e:
        if isinstance(e.cause, temporalio.exceptions.TerminatedError):
            print(f"Workflow {handle.id} was terminated.")
            return f"Workflow {handle.id} was terminated."
        else:
            print(f"Workflow {handle.id} failed with an unexpected error: {e}")
            return f"Workflow {handle.id} failed with an unexpected error."
    

if __name__ == "__main__":
    asyncio.run(consume_kafka_message())
