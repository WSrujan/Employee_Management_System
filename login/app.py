from flask import Flask, request, session, redirect, url_for, render_template, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from sqlalchemy.exc import IntegrityError
from itsdangerous import URLSafeTimedSerializer
from os import environ
from dotenv import load_dotenv
from flask_mail import Mail, Message
from operator import itemgetter


load_dotenv()
app = Flask(__name__)

app.secret_key = environ.get('SECRET_KEY')
app.config['MYSQL_HOST'] = environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = environ.get('MYSQL_DB')

mysql = MySQL(app)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = environ.get('MAIL_PORT')
app.config['MAIL_USERNAME'] = environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = environ.get('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
mail = Mail(app)

# Initialize the serializer
s = URLSafeTimedSerializer(app.secret_key)


@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = % s AND password = % s', (username, password, ))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            msg = 'Logged in successfully !'
            # Check if the user is an admin
            if account['is_admin']:
                # Redirect the admin user to the admin dashboard
                return redirect(url_for('admin_review'))
            else:
                # Redirect the non-admin user to the regular dashboard
                return render_template('index.html', msg = msg)
        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg = msg)

@app.route('/logout')
def logout():
	session.pop('loggedin', None)
	session.pop('id', None)
	session.pop('username', None)
	return redirect(url_for('login'))

@app.route('/new_admin', methods=['GET'])
def new_admin():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    return render_template('new_admin.html')

@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'id' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        employee_id = request.form['id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s OR id = %s', (username, employee_id))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers !'
        elif not username or not password or not email or not employee_id:
            msg = 'Please fill out the form !'
        else:
            cursor.execute('INSERT INTO accounts (id, username, password, email) VALUES (%s, %s, %s, %s)', (employee_id, username, password, email))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)



@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    id = session['id']

    # Create a cursor
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Execute a query to fetch the projects
    cur.execute('SELECT projects.id, projects.name, projects.description FROM projects JOIN project_memberships ON projects.id = project_memberships.project_id WHERE user_id = %s', [id])

    # Fetch all the results
    projects = cur.fetchall()

    # Fetch the members of each project
    for project in projects:
        cur.execute('SELECT username FROM accounts JOIN project_memberships ON accounts.id = project_memberships.user_id WHERE project_id = %s', [project['id']])
        project['members'] = [row['username'] for row in cur.fetchall()]
    
    # Fetch all reports from the database along with their corresponding project
    cur.execute("""
        SELECT reports.*, projects.name 
        FROM reports 
        JOIN projects ON reports.project_id = projects.id
        WHERE username = %s
        ORDER BY reports.timestamp DESC
    """, [username])

    reports = cur.fetchall()

    # Assign the reports to their respective projects
    for project in projects:
        project['reports'] = [report for report in reports if report['project_id'] == project['id']]

    # Get the query from the request arguments
    query = request.args.get('query')
    if query:
        for project in projects:
            project['reports'] = [report for report in project['reports'] if query.lower() in (str(report.get('report_id', '') if report.get('report_id') is not None else '').lower(), str(report.get('id', '') if report.get('id') is not None else '').lower(), (report.get('username', '') if report.get('username') is not None else '').lower(), (report.get('report_text', '') if report.get('report_text') is not None else '').lower(), str(report.get('admin_remark', '') if report.get('admin_remark') is not None else '').lower(), str(report.get('project_id', '') if report.get('project_id') is not None else '').lower(), str(report.get('admin_id', '') if report.get('admin_id') is not None else '').lower(), (report.get('admin_username', '') if report.get('admin_username') is not None else '').lower(), (report.get('name', '') if report.get('name') is not None else '').lower(), project['name'].lower())]


    return render_template('dashboard.html', username=username, projects=projects, id = id)



@app.route('/submit_report', methods=['POST'])
def submit_report():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    username = session['username']
    report_text = request.form['report_text']
    project_id = request.form['project_id']
    id = session['id']

    # Store the report in the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO reports (id, username, report_text, project_id) VALUES (%s, %s, %s, %s)", (id, username, report_text, project_id))
    mysql.connection.commit()
    flash('Report added successfully!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/admin_review')
def admin_review():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Fetch all projects from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()

    # Fetch the members of each project
    for project in projects:
        cur.execute("SELECT username FROM accounts JOIN project_memberships ON accounts.id = project_memberships.user_id WHERE project_id = %s", (project['id'],))
        project['members'] = [row['username'] for row in cur.fetchall()]

    # Fetch all reports from the database along with their corresponding project
    cur.execute("""
    SELECT reports.*, projects.name 
    FROM reports 
    JOIN projects ON reports.project_id = projects.id
    ORDER BY reports.timestamp DESC
""")
    reports = cur.fetchall()

    # Filter the reports based on the query
    query = request.args.get('query')
    if query:
        reports = [report for report in reports if query.lower() in (str(report['report_id']).lower(), str(report['id']).lower(), report['username'].lower() if report['username'] else '', report['report_text'].lower().split() if report['report_text'] else '', str(report['admin_remark']).lower() if report['admin_remark'] else '', str(report['project_id']).lower(), str(report['admin_id']).lower(), report['admin_username'].lower() if report['admin_username'] else '', report['name'].lower() if report['name'] else '')]

    # Replace None with '' in admin_remark
    for report in reports:
        if report['admin_remark'] is None:
            report['admin_remark'] = ''

    return render_template('admin_dashboard.html', reports=reports, projects=projects, username=session['username'])

@app.route('/add_admin', methods=['POST'])
def add_admin():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Get the new admin's details from the form data
    id = request.form['id']
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    # Insert the new admin into the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO accounts (id, username, email, password, is_admin) VALUES (%s, %s, %s, %s, %s)", (id, username, email, password, True))
    mysql.connection.commit()

    flash('New admin added successfully!', 'success')
    return redirect(url_for('new_admin'))

@app.route('/add_remarks', methods=['POST'])
def add_remarks():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Update the report in the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    remark_added = False  # Add a flag for checking if a remark is added
    remark_attempted = False  # Add a flag for checking if a remark was attempted

    for key, value in request.form.items():
        if key.startswith('admin_remark_'):
            remark_attempted = True
            report_id = key.split('_')[-1]
            cur.execute("SELECT admin_remark, admin_username FROM reports WHERE report_id = %s", (report_id,))
            existing_remark = cur.fetchone()['admin_remark']
            if existing_remark is None and value.strip():  # if the existing remark is None and value is not empty
                cur.execute("UPDATE reports SET admin_remark = %s, admin_username = %s WHERE report_id = %s", (value, session['username'], report_id))
                remark_added = True  # Set the flag to True if a remark is added

    # Check the flags to determine which flash message to display
    if remark_added:
        flash('Remark(s) added successfully!', 'success')
    elif remark_attempted:
        flash('Remark(s) not added! Remark cannot be changed!', 'danger')

    mysql.connection.commit()

    return redirect(request.referrer)  # Redirect to the page from where the request came

@app.route('/add_project', methods=['POST'])
def add_project():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Get the project details from the form data
    name = request.form['name']
    description = request.form['description']
    end_date = request.form['end_date']

    # Insert the new project into the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO projects (name, description, end_date) VALUES (%s, %s, %s)", (name, description, end_date))
    mysql.connection.commit()
    flash('New Project added successfully!', 'success')

    # Fetch the updated list of projects
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()

    return render_template('project.html', projects=projects)

@app.route('/delete_project', methods=['POST'])
def delete_project():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Get the project id from the form data
    project_id = request.form['project_id']

    # Create a cursor
    cur = mysql.connection.cursor()

    # Delete the associated records from the project_memberships table
    cur.execute("DELETE FROM project_memberships WHERE project_id = %s", (project_id,))

    # Delete the project from the projects table
    cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))

    # Commit the changes
    mysql.connection.commit()

    # Delete the project from the database
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
    mysql.connection.commit()
    flash('Project deleted successfully!', 'success')

    # Fetch the updated list of projects
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()

    return render_template('project.html', projects=projects)

@app.route('/projects', methods=['GET'])
def projects():
    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Fetch the list of projects
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()

    # Fetch the members of each project
    for project in projects:
        cur.execute("SELECT username FROM accounts JOIN project_memberships ON accounts.id = project_memberships.user_id WHERE project_id = %s", (project['id'],))
        project['members'] = [row['username'] for row in cur.fetchall()]

    return render_template('project.html', projects=projects)

@app.route('/manage_user_assignment', methods=['POST'])
def manage_user_assignment():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Check if the user is an admin
    if not user['is_admin']:
        return redirect(url_for('login'))

    # Get the user id, project id, and operation from the form data
    user_id = request.form['user_id']
    project_id = request.form['project_id']
    operation = request.form['operation']

    # Create a cursor
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check if the user id exists
    cur.execute("SELECT * FROM accounts WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        return "Error: User does not exist."

    # Check if the project id exists
    cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    project = cur.fetchone()
    if not project:
        return "Error: Project does not exist."

    if operation == 'add':
        # Add the user to the project
        try:
            cur.execute("INSERT INTO project_memberships (user_id, project_id) VALUES (%s, %s)", (user_id, project_id))
            mysql.connection.commit()
            flash('This user is added to this project!', 'success')
        except IntegrityError:
            flash('This user is already a member of this project.', 'danger')
            return "Error: This user is already a member of this project."
    elif operation == 'remove':
        # Remove the user from the project
        cur.execute("DELETE FROM project_memberships WHERE user_id = %s AND project_id = %s", (user_id, project_id))
        mysql.connection.commit()
        flash('This user is removed from this project!', 'success')

        # Fetch the updated list of projects
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()

    # Fetch the members of each project
    for project in projects:
        cur.execute("SELECT username FROM accounts JOIN project_memberships ON accounts.id = project_memberships.user_id WHERE project_id = %s", (project['id'],))
        project['members'] = [row['username'] for row in cur.fetchall()]


    return render_template('project.html', projects=projects)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Validate email (check if it exists in the database)
        # Generate a reset token
        token = s.dumps(email, salt='reset-password')
        # Send reset email
        send_reset_email(email, token)
        flash('An email with instructions to reset your password has been sent.', 'success')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='reset-password', max_age=3600)  # Token expires after 1 hour
    except Exception:
        flash('Invalid or expired reset link. Please request a new one.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        # Update user's password in the database
        # (you'll need to hash the password before storing it)
        flash('Your password has been reset successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


def send_reset_email(email, token):
    msg = Message('Password Reset Request', sender='noreply@example.com', recipients=[email])
    reset_link = url_for('reset_password', token=token, _external=True)
    msg.body = f"Click the link below to reset your password:\n{reset_link}"
    mail.send(msg)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user = None  # Initialize user to None
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        # Check if the old password is correct
        if user['password'] == old_password:
            # Update the password in the database
            cur.execute("UPDATE accounts SET password = %s WHERE username = %s", (new_password, session['username']))
            mysql.connection.commit()
            flash('Password changed successfully!', 'success')

            # Check if the user is an admin
            if user and user['is_admin']:
                return redirect(url_for('admin_review'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Incorrect old password!', 'danger')

    return render_template('change_password.html', user=user)

@app.route('/employee_projects')
def employee_projects():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch the current user from the database
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM accounts WHERE username = %s", [session['username']])
    user = cur.fetchone()

    # Fetch all projects associated with the current user from the database
    cur.execute("""
    SELECT projects.* 
    FROM projects 
    JOIN project_memberships ON projects.id = project_memberships.project_id 
    WHERE project_memberships.user_id = %s
    """, [user['id']])
    projects = cur.fetchall()

    for project in projects:
        cur.execute("""
        SELECT GROUP_CONCAT(accounts.username) as members 
        FROM accounts 
        JOIN project_memberships ON accounts.id = project_memberships.user_id 
        WHERE project_memberships.project_id = %s
        """, [project['id']])
        result = cur.fetchone()
        project['members'] = result['members']

    return render_template('employee_projects.html', projects=projects, username=session['username'])

if __name__ == '__main__':
    app.run(debug=True)