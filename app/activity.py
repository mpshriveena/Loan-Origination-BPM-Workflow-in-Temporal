from temporalio import activity
import sqlite3
import urllib.parse
import json
from temporalio.client import Client
from kafka import KafkaProducer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


DATABASE1 = '/userdb.sqlite3'
DATABASE2 = '/transactiondb.sqlite3'

class loanActivities:
    def __init__(self, session):
        self.session = session
        
    @activity.defn
    async def persist_loan_application(loan_data: dict) -> int:
        conn = sqlite3.connect(DATABASE1)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO loan_applications (applicationId, applicantName, email, phone, loanAmount, loanPurpose)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            loan_data['applicationId'],
            loan_data['applicantName'],
            loan_data['email'],
            loan_data['phone'],
            loan_data['loanAmount'],
            loan_data['loanPurpose']
        ))
        conn.commit()
        id = cursor.lastrowid
        conn.close()
        return id

    @activity.defn
    async def is_eligible(self, loan_data: dict) -> dict:
        applicationId = loan_data['applicationId']
        loanAmount = loan_data['loanAmount']
        base = f"http://app:5000/credit_income"
        url = f"{base}?applicationId={urllib.parse.quote(str(applicationId))}"
        async with self.session.get(url) as response:
            response.raise_for_status()
            credit_income_data = await response.json()
            credit_score = credit_income_data['credit_score']
            annual_income = credit_income_data['annual_income']
            isEligible = False
            rejection_reason = None
            if (credit_score > 600) and (loanAmount <= 5*annual_income):
                isEligible = True
            if not isEligible:
                if credit_score < 600:
                    rejection_reason = "Credit score is below 600"
                elif loanAmount > 5 * annual_income:
                    rejection_reason = "Loan amount is greater than 5 times your annual income"
            return {
                "isEligible": isEligible,
                "rejectionReason": rejection_reason,
                "credit_score": credit_score
            }
            
    @activity.defn
    async def loan_pricing(pricing_input: dict) -> dict:
        credit_score = pricing_input['credit_score']
        loan_amount = p = pricing_input['loan_amount']
        loan_tenure = n = pricing_input['loan_tenure']
        manual_approval_terms = pricing_input['manual_approval_terms']
        if credit_score>=750:
            interestRate = 5
            r = 0.05/12
        elif credit_score>=700:
            interestRate = 7
            r = 0.07/12
        elif credit_score>=650:
            interestRate = 9
            r = 0.09/12
        else:
            interestRate = 11
            r = 0.11/12
        monthlyEMI = p*((r*((1+r)**n))/(((1+r)**n)-1))
        return {
                "interestRate": interestRate,
                "loan_tenure": loan_tenure,
                "monthlyEMI": monthlyEMI
            }
    
    @activity.defn
    async def loan_disbursement(disbursement_input: dict) -> dict:
        disbursementStatus = "success"
        paymentStatus = "partiallyPaid"
        conn = sqlite3.connect(DATABASE2)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (loanId, applicantName, email, loanAmount, loanTenure, monthlyEMI, disbursementStatus, paymentStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            disbursement_input['applicationId'],
            disbursement_input['applicantName'],
            disbursement_input['email'],
            disbursement_input['loanAmount'],
            disbursement_input['loanTenure'],
            disbursement_input['monthlyEMI'],
            disbursementStatus,
            paymentStatus
        ))
        conn.commit()
        transactionId = cursor.lastrowid
        conn.close()
        kafka_message = {
                "loanId": disbursement_input['applicationId'],
                "applicantName": disbursement_input['applicantName'],
                "email": disbursement_input['email'],
                "loanAmount": disbursement_input['loanAmount'],
                "loanTenure": disbursement_input['loanTenure'],
                "monthlyEMI": disbursement_input['monthlyEMI'],
                "disbursementStatus": disbursementStatus,
                "transactionId": transactionId
                }
        producer = KafkaProducer(
        bootstrap_servers=['kafka-1:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        topic_name = 'loan_disbursement'
        producer.send(topic_name, kafka_message)
        producer.flush()
        producer.close()
        return kafka_message
    
class emailActivities:  
    @activity.defn
    async def send_email(kafka_message: dict) -> dict:
        receiver_email = kafka_message["emailRecipient"]
        sender_email = "21f3001238@ds.study.iitm.ac.in"
        password = "fxxh qnlp bfnd zuls"
        subject = kafka_message["subject"]
        body = kafka_message["body"]
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, msg.as_string())
                print(f"Email sent to {receiver_email} successfully!")
                return {"Email sent successfully to": receiver_email}

        except Exception as e:
            print(f"Error sending email: {e}")
            return {"message": e }
    
    @activity.defn
    async def status_update(loanId):
        conn = sqlite3.connect(DATABASE2)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transactions
            SET paymentStatus = 'paidInFull'
            WHERE loanId = ?
        ''', (loanId,))
        conn.commit()
        return {"message": "updated database"}
        
    @activity.defn
    async def cancel_schedule(loanId):
        await cancel_function(loanId)
        
    
async def cancel_function(loanId):
    client = await Client.connect("temporal:7233")  # Adjust for your server
    workflow_id = f"loan-email-workflow{loanId}"
    try:
        handle =  client.get_workflow_handle(workflow_id)
        await handle.terminate(reason="Terminating Cron Workflow")
        print(f"Cancellation request has been sent to Workflow {workflow_id}")
    except Exception as e:
        print(f"Error while canceling workflow: {e}")
        



