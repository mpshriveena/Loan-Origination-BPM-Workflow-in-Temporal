import sqlite3

DATABASE1 = 'userdb.sqlite3'
DATABASE2 = 'transactiondb.sqlite3'
DATABASE3 = 'commentsdb.sqlite3'


def init_db():
    conn = sqlite3.connect(DATABASE1)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loan_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicationId TEXT NOT NULL,
            applicantName TEXT NOT NULL,
            email TEXT NOT NULL,
            phone INTEGER NOT NULL,
            loanAmount INTEGER NOT NULL,
            loanPurpose TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    
    conn = sqlite3.connect(DATABASE2)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transactionId INTEGER PRIMARY KEY AUTOINCREMENT,
            loanId TEXT NOT NULL,
            applicantName TEXT NOT NULL,
            email TEXT NOT NULL,
            loanAmount INTEGER NOT NULL,
            loanTenure INTEGER NOT NULL,
            monthlyEMI TEXT NOT NULL,
            disbursementStatus TEXT NOT NULL,
            paymentStatus TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    
    conn = sqlite3.connect(DATABASE3)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviewer_comments (
            commentsId INTEGER PRIMARY KEY AUTOINCREMENT,
            loanId TEXT NOT NULL,
            reviewerId TEXT NOT NULL,
            approvalStatus TEXT NOT NULL,
            comments TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    

if __name__ == "__main__":
    init_db()