from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
import os
from models import db, User, BugReport
from forms import LoginForm, RegistrationForm, BugReportForm, EditBugForm, BugSearchForm
from config import Config
from sqlalchemy import func, extract
import plotly
import plotly.graph_objs as go
import json
from sqlalchemy import func
import datetime

import calendar
from werkzeug.utils import secure_filename
import os



def month_number_to_name(month_num):
    return calendar.month_name[month_num]


app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    search_form = BugSearchForm(formdata=request.form if request.method == 'POST' else request.args)
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Or another suitable number of items per page
    
    query = BugReport.query.filter_by(user_id=current_user.id)
    
    # Apply filters from search_form using case-insensitive comparison
    if request.method == 'POST' or request.method == 'GET':
        if search_form.keyword.data:
            # Use func.lower for case-insensitive search on the title
            query = query.filter(func.lower(BugReport.title).contains(func.lower(search_form.keyword.data)))
        if search_form.status.data and search_form.status.data != 'All':
            # Use func.lower for case-insensitive comparison on the status
            query = query.filter(func.lower(BugReport.status) == func.lower(search_form.status.data))
        if search_form.severity.data and search_form.severity.data != 'All':
            # Use func.lower for case-insensitive comparison on the severity
            query = query.filter(func.lower(BugReport.severity) == func.lower(search_form.severity.data))
    
    pagination = query.order_by(BugReport.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    bugs = pagination.items

    return render_template('dashboard.html', bugs=bugs, search_form=search_form, pagination=pagination)




@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:  # This should use hashed passwords in a real app
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)  # Hash passwords in real app
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/submit_bug', methods=['GET', 'POST'])
@login_required
def submit_bug():
    form = BugReportForm()
    if form.validate_on_submit():
        # Handling file uploads
        screenshot = form.screenshot.data
        screen_recording = form.screen_recording.data
        screenshot_filename, screen_recording_filename = None, None

        if screenshot:
            screenshot_filename = secure_filename(screenshot.filename)
            screenshot.save(os.path.join(app.config['UPLOAD_FOLDER'], screenshot_filename))

        if screen_recording:
            screen_recording_filename = secure_filename(screen_recording.filename)
            screen_recording.save(os.path.join(app.config['UPLOAD_FOLDER'], screen_recording_filename))
        
        # Creating the bug report with file paths and other details
        bug = BugReport(
            title=form.title.data, 
            description=form.description.data, 
            user_id=current_user.id, 
            severity=form.severity.data, 
            status=form.status.data,
            screenshot_path=screenshot_filename, 
            screen_recording_path=screen_recording_filename
        )
        
        # Save the bug to the database
        db.session.add(bug)
        
        # Update user points
        current_user.points += 10  # Assuming 'points' field exists in User model
        
        db.session.commit()
        
        flash('Your bug report has been submitted.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('submit_bug.html', form=form)


@app.route('/edit_bug/<int:bug_id>', methods=['GET', 'POST'])
@login_required
def edit_bug(bug_id):
    bug = BugReport.query.get_or_404(bug_id)
    if bug.user_id != current_user.id:
        flash('You can only edit your own bug reports.')
        return redirect(url_for('dashboard'))
    form = EditBugForm()
    if form.validate_on_submit():
        bug.title = form.title.data
        bug.description = form.description.data
        bug.status = form.status.data
        db.session.commit()
        flash('Your bug report has been updated.')
        return redirect(url_for('dashboard'))
    elif request.method == 'GET':
        form.title.data = bug.title
        form.description.data = bug.description
        form.status.data = bug.status
    return render_template('edit_bug.html', form=form)

@app.route('/leaderboard')
def leaderboard():
    top_users = User.query.order_by(User.points.desc()).limit(10).all()
    print("Top Users:", top_users)
    return render_template('leaderboard.html', top_users=top_users)

@app.route('/bug/<int:bug_id>/attachments')
@login_required
def view_attachments(bug_id):
    bug = BugReport.query.get_or_404(bug_id)
    if bug.user_id != current_user.id:
        flash('You do not have permission to view these attachments.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('view_attachments.html', bug=bug)



@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/trend_analysis')
@login_required
def trend_analysis():
    # Fetch and process data for the graph by severity
    results_severity = db.session.query(
        extract('month', BugReport.created_at).label('month'),
        BugReport.severity,
        func.count().label('count')
    ).group_by('month', BugReport.severity).order_by('month').all()

    data_severity = []
    for month_num, severity, count in results_severity:
        month_name = calendar.month_name[month_num]
        existing_trace = next((item for item in data_severity if item['name'] == severity), None)
        if existing_trace:
            existing_trace['y'][month_num-1] += count
        else:
            new_trace = {
                'x': [calendar.month_name[i] for i in range(1, 13)],
                'y': [0]*12,
                'type': 'bar',
                'name': severity
            }
            new_trace['y'][month_num-1] = count
            data_severity.append(new_trace)

    # Fetch and process data for the graph by status
    results_status = db.session.query(
        extract('month', BugReport.created_at).label('month'),
        BugReport.status,
        func.count().label('count')
    ).group_by('month', BugReport.status).order_by('month').all()

    data_status = []
    for month_num, status, count in results_status:
        month_name = calendar.month_name[month_num]
        existing_trace = next((item for item in data_status if item['name'] == status), None)
        if existing_trace:
            existing_trace['y'][month_num-1] += count
        else:
            new_trace = {
                'x': [calendar.month_name[i] for i in range(1, 13)],
                'y': [0]*12,
                'type': 'bar',
                'name': status
            }
            new_trace['y'][month_num-1] = count
            data_status.append(new_trace)

    graph_severity_json = json.dumps({
        'data': data_severity,
        'layout': {
            'title': 'Bug Reports by Severity',
            'barmode': 'group',
            'yaxis': {
                'tickformat': ',d'  # Format ticks as integers
            }
        }
    }, cls=plotly.utils.PlotlyJSONEncoder)

    graph_status_json = json.dumps({
        'data': data_status,
        'layout': {
            'title': 'Bug Reports by Status',
            'barmode': 'group',
            'yaxis': {
                'tickformat': ',d'  # Format ticks as integers
            }
        }
    }, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('trend_analysis.html', 
                           graph_severity_json=graph_severity_json, 
                           graph_status_json=graph_status_json)




if __name__ == '__main__':
    app.run(debug=True)
