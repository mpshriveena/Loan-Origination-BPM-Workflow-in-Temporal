from datetime import timedelta
from temporalio import workflow
from activity import loanActivities, emailActivities
import asyncio
from temporalio.client import Client
import temporalio
import subprocess



@workflow.defn
class LoanWorkflow:
    def __init__(self):
        self.workflow_status = "started"
        self.result = {}
        
        
    @workflow.run
    async def run(self, loan_data: dict) -> dict:
        print(f"Workflow Status: {self.workflow_status}")
        id = await workflow.execute_activity_method(
            loanActivities.persist_loan_application,
            loan_data,
            start_to_close_timeout=timedelta(seconds=10000),
        )
        print(f"Persisted Loan Application ; Automated Generated Id: {id}")
        print(f"Workflow Status: {self.workflow_status}")
        eligibity_details = await workflow.execute_activity_method(
            loanActivities.is_eligible,
            loan_data,
            start_to_close_timeout=timedelta(seconds=10000),
        )
        self.result = eligibity_details
        print(f"Eligibility Information Obtained : {eligibity_details}")
        print(f"Workflow Status: {self.workflow_status}")
        if not eligibity_details['isEligible']:
            self.workflow_status="finished"
        else:
            self.workflow_status="waiting_for_manual_approval"
            print(f"Waiting for manual approval")
            print(f"Workflow Status: {self.workflow_status}")
        while self.workflow_status=="waiting_for_manual_approval":
            await workflow.sleep(1)
        persist_comments_data = {'loanId':loan_data['applicationId'],
                                 'reviewerId':self.result['reviewerId'],
                                 'approvalStatus':self.result['approvalStatus'],
                                 'comments':self.result['comments'],}
        persist_confirmation = await workflow.execute_activity_method(
            loanActivities.persist_reviewer_comments,
            persist_comments_data,
            start_to_close_timeout=timedelta(seconds=10000),
        )
        if self.workflow_status == "manually_approved":
            print(f"Workflow Status: {self.workflow_status}")
            self.workflow_status = "loan_pricing"
            credit_score = eligibity_details['credit_score']
            loan_amount = loan_data['loanAmount']
            loan_tenure = 12
            manual_approval_terms = "Pay correctly"
            pricing_input = {
                "credit_score" : credit_score,
                "loan_amount" : loan_amount,
                "loan_tenure" : loan_tenure,
                "manual_approval_terms" : manual_approval_terms
            }
            pricing_output = await workflow.execute_activity_method(
            loanActivities.loan_pricing,
            pricing_input,
            start_to_close_timeout=timedelta(seconds=10000),
                )
            self.result = pricing_output
            print(f"Pricing output: {pricing_output}")
            self.workflow_status = "waiting_for_confirmation"
        print(f"Workflow Status: {self.workflow_status}")
        while self.workflow_status=="waiting_for_confirmation":
            await workflow.sleep(1)
        if self.workflow_status == "confirmed":
            print(f"Workflow Status: {self.workflow_status}")
            applicationId = loan_data['applicationId']
            applicantName = loan_data['applicantName']
            email = loan_data['email']
            loanAmount = loan_data['loanAmount']
            loanTenure = pricing_output['loan_tenure']
            monthlyEMI = pricing_output['monthlyEMI']
            disbursement_input = {
                "applicationId" : applicationId,
                "applicantName" : applicantName,
                "email" : email,
                "loanAmount" : loanAmount,
                "loanTenure" : loanTenure,
                "monthlyEMI" : monthlyEMI
                }
            disbursement_output = await workflow.execute_activity_method(
            loanActivities.loan_disbursement,
            disbursement_input,
            start_to_close_timeout=timedelta(seconds=10000),
            )
            self.result = disbursement_output
            print(f"Pricing output: {disbursement_output}")
            self.workflow_status="finished"
        if self.workflow_status == "finished":
            print(f"Final Result: {self.result}")
            return self.result
    
    @workflow.signal
    async def manual_approval(self, approval_data: dict):
        print(f"Received a signal for manual approval")
        approval_status = approval_data['approvalStatus']
        print(f"The approval status is {approval_status}")
        if approval_status=="approved":
            self.result = approval_data
            self.workflow_status = "manually_approved"
        if approval_status=="rejected":
            self.result = approval_data
            self.workflow_status = "finished"
            
    @workflow.signal
    async def e_signature(self):
        self.workflow_status = "confirmed"
        
@workflow.defn
class EmailNotificationWorkflow:
    def __init__(self):
        self.email_status = "started"
        self.result = {}
        self.full_paid = False
        self.loanId = 0
        
    @workflow.run
    async def run(self, kafka_message: dict) -> dict:
        if self.full_paid:
            paid_status_update = await workflow.execute_activity_method(
            emailActivities.status_update,
            self.loanId,
            start_to_close_timeout=timedelta(seconds=10000),
        )
            cancel_output = await workflow.execute_activity_method(
            emailActivities.cancel_schedule,
            self.loanId,
            start_to_close_timeout=timedelta(seconds=10000),
        )
            self.result = cancel_output
            print(f"Cancel Output: {cancel_output}")
            return {
                    "cancel_output" : cancel_output,
                    "full_paid" : self.full_paid
                }
        
        email_output = await workflow.execute_activity_method(
            emailActivities.send_email,
            kafka_message,
            start_to_close_timeout=timedelta(seconds=10000),
        )
        self.result = email_output
        print(f"Email Output: {email_output}")
        return {
                "email_output" : email_output,
                "full_paid" : self.full_paid
            }
    
    @workflow.signal
    async def cancel_email_workflows(self, signal_data: dict):
        print(f"Received signal to terminate workflow for loanId: {signal_data['loanId']}")
        workflow_id = f"loan-email-workflow{signal_data['loanId']}"
        print(f"{signal_data['paymentStatus']}")
        self.loanId = signal_data['loanId']
        if signal_data['paymentStatus']=='paidInFull':
            self.full_paid = True
        
        
