
# app.py
from flask import Flask, render_template, request, send_from_directory, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import os
from collections import deque
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['SECRET_KEY'] = 'your_secret_key'  # Add a secret key for flash messages
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class DeletedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    deletion_date = db.Column(db.DateTime, default=datetime.utcnow)

def bfs_search_by_date(graph, start, target_date):
    visited = set()
    queue = deque([start])
    result_files = []

    while queue:
        current_file = queue.popleft()

        file_info = File.query.filter_by(filename=current_file).first()
        if file_info.upload_date.date() == target_date:
            result_files.append(file_info)

        connected_files = graph.get(current_file, [])
        for connected_file in connected_files:
            if connected_file not in visited:
                queue.append(connected_file)
                visited.add(connected_file)

    return result_files

@app.route('/')
def index():
    existing_files = File.query.all()
    deleted_files = DeletedFile.query.all()
    return render_template('index.html', existing_files=existing_files, deleted_files=deleted_files)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))

    existing_file = File.query.filter_by(filename=file.filename).first()
    if existing_file is None:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        new_file = File(filename=file.filename)
        db.session.add(new_file)
        db.session.commit()
        flash('File uploaded successfully!', 'success')
        print(f"File saved to: {file_path}")  # Add this line for debugging
    else:
        flash('File with the same name already exists. Please choose a different name.', 'error')

    return redirect(url_for('index'))

# ...

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/search', methods=['POST'])
def search_by_date():
    search_date = request.form['search_date']
    search_date = datetime.strptime(search_date, '%Y-%m-%d')
    deleted_files = DeletedFile.query.filter(DeletedFile.deletion_date >= search_date, DeletedFile.deletion_date < search_date + timedelta(days=1)).all()
    existing_files = File.query.all()
    return render_template('index.html', deleted_files=deleted_files, existing_files=existing_files)

@app.route('/delete/<int:file_id>')
def delete_file(file_id):
    file_to_delete = File.query.get_or_404(file_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_to_delete.filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    deleted_file = DeletedFile(filename=file_to_delete.filename)
    db.session.add(deleted_file)

    db.session.delete(file_to_delete)
    db.session.commit()

    flash('File deleted successfully!', 'success')
    return redirect(url_for('index'))
# app.py

# ...

@app.route('/search_deleted', methods=['POST'])
def search_deleted_by_date():
    search_date = request.form['search_date']
    search_date = datetime.strptime(search_date, '%Y-%m-%d')
    deleted_files = DeletedFile.query.filter(DeletedFile.deletion_date >= search_date, DeletedFile.deletion_date < search_date + timedelta(days=1)).all()
    existing_files = File.query.all()
    return render_template('index.html', deleted_files=deleted_files, existing_files=existing_files)

@app.route('/recover/<int:file_id>')
def recover_file(file_id):
    deleted_file = DeletedFile.query.get_or_404(file_id)

    # Periksa apakah file sudah ada di file yang ada
    existing_file = File.query.filter_by(filename=deleted_file.filename).first()
    if existing_file:
        flash('File dengan nama yang sama sudah ada. Harap pilih nama yang berbeda.', 'error')
        return redirect(url_for('index'))

    # Pulihkan file
    recovered_file = File(filename=deleted_file.filename)
    db.session.add(recovered_file)
    db.session.delete(deleted_file)
    db.session.commit()

    flash('File berhasil dipulihkan!', 'success')
    return redirect(url_for('index'))

@app.route('/download_deleted/<filename>')
def download_deleted_file(filename):
    deleted_file = DeletedFile.query.filter_by(filename=filename).first()

    if deleted_file:
        deleted_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if os.path.exists(deleted_file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
        else:
            flash('File not found in the directory', 'error')
            return redirect(url_for('index'))
    else:
        flash('File not found in the database', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)