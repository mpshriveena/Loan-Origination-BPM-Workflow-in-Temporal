from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import asyncio
import sys
from temporalio.client import Client
from activity_workflow import LoanWorkflow  # Import your workflow

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user' 
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.String, unique=True)    
    username = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    phone = db.Column(db.Integer, unique=True)
    credit_score = db.Column(db.Integer)
    annual_income = db.Column(db.Float)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loandb.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

app.config['SECRET_KEY'] = 'secretkey'
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_PASSWORD_SALT'] = 'somesalt'
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'

db.init_app(app)

@app.route('/apply', methods=['POST'])
async def apply_loan():
    try:
        loan_data = request.json
        applicationId = loan_data.get('applicationId')
        client = await Client.connect("temporal:7233")
        handle = await client.start_workflow(
        LoanWorkflow.run,
        loan_data,
        id=f"loan-workflow{applicationId}",
        task_queue="loan-task-queue",
    )    
        print(f"Started workflow. Workflow ID: {handle.id}, RunID: {handle.result_run_id}")
        result = await handle.result()
        return(f"Result: {result}")
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


@app.route('/credit_income', methods=['GET'])
def credit_income():
    applicationId = request.args.get('applicationId', None)
    user = User.query.filter_by(applicant_id=applicationId).first()
    credit_score = user.credit_score
    annual_income = user.annual_income
    return jsonify({"credit_score": credit_score,"annual_income": annual_income})
    
with app.app_context():
    db.create_all()
    
    if not User.query.filter_by(applicant_id="354").first():
        user_123 = User(
            applicant_id="354",
            username="M P Shri Veena",
            email="mpshriveena@gmail.com",
            phone=7845573332,
            credit_score=700,
            annual_income=1000000)
        db.session.add(user_123)

    if not User.query.filter_by(applicant_id="9232").first():
        user_9232 = User(
            applicant_id="9232",
            username="Divya",
            email="divya@gmail.com",
            phone=7586236541,
            credit_score=0,
            annual_income=84000)
        db.session.add(user_9232)

    if not User.query.filter_by(applicant_id="5265").first():
        user_5265 = User(
            applicant_id="5265",
            username="Sreedevi",
            email="sreedevi@gmail.com",
            phone=9642351789,
            credit_score=520,
            annual_income=9600000)
        db.session.add(user_5265)
    
    db.session.commit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug = True)
