from flask import Flask,request,send_from_directory,jsonify,abort,send_file
from flask_pymongo import PyMongo,MongoClient
import os
import gridfs
import shutil
from flask_cors import CORS
import zipfile
from PyPDF2 import PdfMerger
from bson import ObjectId
from working2 import create_translated_pdf
import subprocess

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = "C:/Users/arjun/OneDrive/Desktop/my files/college files/semester 5/Software development/SPAnslate/backend/inputfiles/"
DOWNLOAD_FOLDER = "C:/Users/arjun/OneDrive/Desktop/my files/college files/semester 5/Software development/SPAnslate/backend/outputfiles/"
ZIP_FOLDER = "C:/Users/arjun/OneDrive/Desktop/my files/college files/semester 5/Software development/SPAnslate/backend/zipfiles/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['ZIP_FOLDER'] = ZIP_FOLDER
app.config["MONGO_URI"] = "mongodb://localhost:27017/spanslate"
mongo = PyMongo(app)
client = MongoClient('mongodb://localhost:27017/')
db = client['spanslate']
fs = gridfs.GridFS(db)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdfs' not in request.files:
        return '',400

    files = request.files.getlist('pdfs')
    for file in files:
        if file.filename == '':
            return '',400
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
    for filename in os.listdir(app.config['DOWNLOAD_FOLDER']):
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    files=os.listdir(app.config['UPLOAD_FOLDER'])
    return jsonify(files=files),200

@app.route("/translatepdfs", methods=['POST'])
def getname():
    data = request.get_json()
    lang=data.get("lang")
    files=os.listdir(app.config['UPLOAD_FOLDER'])
    if len(files) == 0:
        return '',410
    for filename in files:
        if filename.lower().endswith('.pdf'):
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            new_filename = f"{os.path.splitext(filename)[0]}_output.pdf"
            new_path = os.path.join(app.config['DOWNLOAD_FOLDER'], new_filename)
            create_translated_pdf(old_path, new_path, lang)
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    return "",200

@app.route("/getfiles",methods=['GET'])
def getfile():
    files = os.listdir(app.config['DOWNLOAD_FOLDER'])
    return jsonify(files=files),200

@app.route("/profilename", methods=['POST'])
def profilename():
    data = request.get_json().get("id")
    id=ObjectId(data)
    account=list(mongo.db.login.find({"_id":id}))
    return jsonify(name=account[0]['name']),200

@app.route('/download', methods=['POST'])
def download():
    for filename in os.listdir(app.config['ZIP_FOLDER']):
        file_path = os.path.join(app.config['ZIP_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    files=request.get_json().get('files')
    download_folder = app.config['DOWNLOAD_FOLDER']
    zip_folder = app.config["ZIP_FOLDER"]
    if len(files) == 1:
        return send_from_directory(download_folder, files[0], as_attachment=True)
    elif len(files) > 1:
        zip_filename = "selected_files2.zip"
        zip_filepath = os.path.join(zip_folder, zip_filename)
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files:
                file_path = os.path.join(download_folder, file)
                if os.path.isfile(file_path):  
                    zipf.write(file_path, file)
        return send_from_directory(zip_folder, zip_filename, as_attachment=True)
    return "", 204

@app.route('/pdf/<path:filename>')
def view_pdf(filename):
    f1 = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f2 = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    if os.path.exists(f1):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    elif os.path.exists(f2):
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename)
    return "File not found", 404

@app.route('/login',methods=['POST'])
def login():
    data = request.get_json()
    user = data.get('user')
    password = data.get('password')
    account=mongo.db.login.find({"user":user})
    account_list = list(account)
    if len(account_list) == 0:
        return jsonify(id=401),401
    for scc in account_list:
        if scc['password']==password:
            id=str(scc["_id"])
            return jsonify(id=id),200
    return jsonify(id=402),401

@app.route("/signup",methods=['POST'])
def signup():
    data = request.get_json()
    name=data.get("name")
    user=data.get("user")
    password=data.get("password")
    account=mongo.db.login.insert_one({
        "name":name,
        "user":user,
        "password":password
    })
    id=str(account.inserted_id)
    return jsonify(id=id),200

@app.route("/send", methods=['POST'])
def send():
    files = request.get_json().get('files')
    user_id = request.get_json().get("id")
    user_id=user_id
    try:
        if files and len(files) > 0:
            for f in files:
                f_path = os.path.join(app.config['DOWNLOAD_FOLDER'], f)
                if os.path.exists(f_path):
                    with open(f_path, 'rb') as file_data:
                        file_id = fs.put(file_data, filename=f, userid=user_id)
                        db.files.insert_one({
                            "userid": user_id,
                            "filename": f,
                            "file_id": file_id
                        })
            return '', 200
        else:
            return '', 402
    except Exception as e:
        print(e)
        return '', 401

@app.route("/save/<user_id>", methods=['GET'])
def download_files(user_id):
    for filename in os.listdir(app.config['DOWNLOAD_FOLDER']):
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    try:
        files = list(db.files.find({"userid": user_id}))
        if not files:
            return jsonify({"message": "No files found for this user"}), 404
        downloaded_files = []
        for file_record in files:
            filename = file_record.get("filename")
            file_id = file_record.get("file_id")
            if not filename or not file_id:
                continue
            file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
            if not os.path.exists(file_path):
                try:
                    file_data = fs.get(file_id)
                    with open(file_path, 'wb') as file:
                        file.write(file_data.read())
                    downloaded_files.append(filename)
                except Exception as e:
                    print(f"Error saving file {filename}: {e}")
            else:
                downloaded_files.append(filename)
        return jsonify({"downloaded_files": downloaded_files}), 200

    except Exception as e:
        print(e)
        return jsonify({"error": "An error occurred while downloading files"}), 500
    
@app.route("/merge", methods=["POST"])
def merge():
    try:
        files = request.get_json().get("files")
        flag=0
        merger = PdfMerger()
        for filename in files:
            file_path1 = os.path.join(DOWNLOAD_FOLDER, filename)
            file_path2 = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(file_path1):
                merger.append(file_path1)
            elif os.path.exists(file_path2):
                merger.append(file_path2)
                flag=1
            else:
                return jsonify({"error": f"File {filename} not found"}), 404
        merged_filename = "_".join(files)
        merged_filename = merged_filename.replace(".pdf",'')+ ".pdf"
        merged_file_path = os.path.join(DOWNLOAD_FOLDER, merged_filename)
        with open(merged_file_path, "wb") as f:
            merger.write(f)
        merger.close()
        
        return jsonify({"merged_file": merged_filename}), 200
    except Exception as e:
        print(e)
        return '',400
    
if __name__ == "__main__":
    app.run(debug=True)