from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import pandas as pd
import qrcode

app = Flask(__name__, static_folder='qr_codes', static_url_path='/qr_codes')

# Directory to save QR code images
output_dir = 'qr_codes'
os.makedirs(output_dir, exist_ok=True)

# Directory to store uploaded files
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Define the allowed extensions for uploaded files
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        organization = request.form.get('organization', '')  # Get organization if provided
        
        # Generate QR code for the participant
        qr_filename = generate_qr_code(name, organization)
        
        # Create a DataFrame with participant data
        participant_data = pd.DataFrame({'Name': [name], 'Organization': [organization], 'QR_Code': [qr_filename]})
        
        # Append participant data to registration_data
        global registration_data
        registration_data = pd.concat([registration_data, participant_data], ignore_index=True)
        
        return render_template('thank_you.html', qr_filename=qr_filename)
    return render_template('register.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # Global declaration of registration_data
        global registration_data
        
        # Handle file upload
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            # Check if the file has a permitted extension
            if '.' in uploaded_file.filename and \
               uploaded_file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
                # Save the uploaded Excel file
                excel_filename = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
                uploaded_file.save(excel_filename)
                
                # Load the registration data from the Excel file
                try:
                    excel_data = pd.read_excel(excel_filename)
                    
                    # Generate QR code for each participant and save it
                    for index, row in excel_data.iterrows():
                        qr_filename = generate_qr_code(row['Name'], row.get('Organization', ''))
                        participant_data = pd.DataFrame({'Name': [row['Name']], 'Organization': [row.get('Organization', '')], 'QR_Code': [qr_filename]})
                        registration_data = pd.concat([registration_data, participant_data], ignore_index=True)
                    
                    return redirect(url_for('admin'))
                except Exception as e:
                    return f"An error occurred while processing the uploaded Excel file: {str(e)}"
            else:
                return "Invalid file extension. Please upload an Excel file."
        else:
            return "No file uploaded."
    else:
        return render_template('admin.html', data=registration_data)

@app.route('/delete/<int:index>', methods=['GET'])
def delete_participant(index):
    # Global declaration of registration_data
    global registration_data
    
    registration_data = registration_data.drop(index)
    return redirect(url_for('admin'))

@app.route('/scanner', methods=['GET'])
def scanner():
    return render_template('scanner.html')

@app.route('/process_scanned_data', methods=['POST'])
def process_scanned_data():
    scanned_data = request.json.get('data')  # Get the scanned data from the request
    name = scanned_data['Name']
    organization = scanned_data['Organization']
    qr_code = ''  # Since it's a one-time scan, no need to store the QR code
    
    # Global declaration of registration_data
    global registration_data
    
    # Check if the participant is already registered
    if ((registration_data['Name'] == name) & (registration_data['Organization'] == organization)).any():
        return jsonify({'message': 'Participant already registered'})
    
    # Record the time and date of the scan
    scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create a DataFrame for the scanned data
    scanned_df = pd.DataFrame({'Name': [name], 'Organization': [organization], 'QR_Code': [qr_code], 'Scan_Time': [scan_time]})
    
    # Concatenate scanned data with registration_data
    registration_data = pd.concat([registration_data, scanned_df], ignore_index=True)
    
    # Save registration data to Excel file
    excel_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'scanned_data.xlsx')
    registration_data.to_excel(excel_filename, index=False)
    
    return jsonify({'message': 'Scanned data received and saved successfully'})

def generate_qr_code(name, organization=''):
    # Construct participant information
    participant_info = f"Name: {name}\nOrganization: {organization}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(participant_info)
    qr.make(fit=True)
    
    # Create QR code image filename
    qr_filename = f"{name}_{organization}.png"
    qr_path = os.path.join(output_dir, qr_filename)
    
    # Save the QR code image
    qr.make_image(fill_color="black", back_color="white").save(qr_path)
    
    # Return the filename
    return qr_filename

# Global declaration of registration_data
registration_data = pd.DataFrame(columns=['Name', 'Organization', 'QR_Code', 'Scan_Time'])

if __name__ == '__main__':
    app.run(debug=True)
