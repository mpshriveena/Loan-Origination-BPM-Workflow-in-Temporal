import asyncio
import aiohttp


from temporalio.client import Client
from temporalio.worker import Worker
from activity import loanActivities, emailActivities
from activity_workflow import LoanWorkflow, EmailNotificationWorkflow

async def main():
    client = await Client.connect("temporal:7233", namespace="default")
    async with aiohttp.ClientSession() as session:
        loanactivities = loanActivities(session)
        print(f"Starting Worker...")
        worker = Worker(
            client,
            task_queue="loan-task-queue",
            workflows=[LoanWorkflow,EmailNotificationWorkflow],
            activities=[loanActivities.persist_loan_application,
                        loanactivities.is_eligible,
                        loanActivities.persist_reviewer_comments,
                        loanActivities.loan_pricing,
                        loanActivities.loan_disbursement,
                        emailActivities.send_email,
                        emailActivities.cancel_schedule,
                        emailActivities.status_update],
        )
        await worker.run()
if __name__ == "__main__":
    asyncio.run(main())
