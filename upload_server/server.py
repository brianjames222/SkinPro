from flask import Flask, request, render_template, jsonify
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image, ExifTags
import json
import sys
import logging
from tkinter import Tk, messagebox

DB_PATH = None
UPLOAD_BASE_DIR = None
PROFILE_PIC_DIR = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_data_paths():
    """Ensure config is loaded from external SkinProData and fallback if needed."""
    fallback_config_path = os.path.expanduser("~/SkinProData/config.json")

    if not os.path.exists(fallback_config_path):
        raise FileNotFoundError("❌ config.json not found in expected location.")

    with open(fallback_config_path, "r") as f:
        config = json.load(f)

    data_dir = config.get("data_dir")
    if not data_dir or not os.path.exists(data_dir):
        raise FileNotFoundError(f"❌ data_dir not found or invalid in config.json: {data_dir}")

    paths_path = os.path.join(data_dir, "paths.json")
    if not os.path.exists(paths_path):
        fallback_paths = {
            "database": os.path.join(data_dir, "skinpro.db"),
            "photos": os.path.join(data_dir, "images"),
            "profile_pictures": os.path.join(data_dir, "profile_pictures")
        }
        with open(paths_path, "w") as f:
            json.dump(fallback_paths, f, indent=2)

    with open(paths_path, "r") as f:
        paths = json.load(f)

    return (
        paths["database"],
        paths["photos"],
        paths.get("profile_pictures", os.path.join(data_dir, "profile_pictures"))
    )


app = Flask(__name__)
@app.route('/upload', methods=['GET', 'POST'])
def upload_photos():
    client_id = request.args.get('cid')
    appointment_id = request.args.get('aid')

    if not client_id or not appointment_id:
        return jsonify({"status": "error", "message": "Missing client or appointment ID"}), 400

    if request.method == 'POST':
        files = request.files.getlist('photos')
        saved_files = []

        # Fetch client name and appointment date
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()

            cursor.execute("SELECT full_name FROM clients WHERE id = ?", (client_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"status": "error", "message": "Client not found"}), 404
            full_name = result[0]

            cursor.execute("SELECT date, type FROM appointments WHERE id = ?", (appointment_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"status": "error", "message": "Appointment not found"}), 404
            raw_date, appt_type = result

            conn.close()

        except Exception as e:
            return jsonify({"status": "error", "message": f"Database error: {e}"}), 500

        # Format folder names
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in full_name).replace(" ", "_")
        formatted_date = raw_date.replace("/", "-")

        # Create upload directory
        target_dir = os.path.join(
            UPLOAD_BASE_DIR,
            f"{safe_name}_id_{client_id}",
            formatted_date
        )
        os.makedirs(target_dir, exist_ok=True)

        successful_upload = False

        for file in files:
            if not file:
                continue

            filename = secure_filename(file.filename)
            save_path = os.path.join(target_dir, filename)

            # Ensure unique filename
            counter = 1
            while os.path.exists(save_path):
                name, ext = os.path.splitext(filename)
                save_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                counter += 1

            try:
                # Save original file
                file.save(save_path)

                # Open with PIL and check for EXIF orientation
                try:
                    image = Image.open(save_path)
                    for orientation in ExifTags.TAGS.keys():
                        if ExifTags.TAGS[orientation] == 'Orientation':
                            break

                    exif = image._getexif()
                    if exif is not None:
                        orientation_value = exif.get(orientation, None)
                        if orientation_value == 3:
                            image = image.rotate(180, expand=True)
                        elif orientation_value == 6:
                            image = image.rotate(270, expand=True)
                        elif orientation_value == 8:
                            image = image.rotate(90, expand=True)
                        image.save(save_path)
                        print(f"✅ Orientation fixed for: {save_path}")
                    else:
                        print(f"ℹ No EXIF orientation found for: {save_path}")
                except Exception as e:
                    print(f"⚠️ Could not fix orientation for {filename}: {e}")

                # Insert into DB
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO photos (client_id, appointment_id, appt_date, file_path, type)
                    VALUES (?, ?, ?, ?, ?)
                """, (client_id, appointment_id, raw_date, save_path, appt_type))
                conn.commit()
                conn.close()

                # Mark as successful only if everything worked
                saved_files.append(save_path)
                successful_upload = True
                print(f"✅ Photo saved and logged: {save_path}")

            except Exception as e:
                print(f"❌ Failed to process photo {filename}: {e}")

        # Update appointment flag
        if successful_upload:
            try:
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("UPDATE appointments SET photos_taken = 'Yes' WHERE id = ?", (appointment_id,))
                conn.commit()
                conn.close()
                print(f"📸 Updated photos_taken = 'Yes' for appointment {appointment_id}")
            except Exception as e:
                print(f"❌ Failed to update photos_taken: {e}")

        return render_template(
            'upload_success.html',
            uploaded=len(saved_files),
            full_name=full_name,
            appointment_date=raw_date,
            appt_type=appt_type
        )

    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute("SELECT full_name FROM clients WHERE id = ?", (client_id,))
        result = cursor.fetchone()
        if not result:
            return "Client not found", 404
        full_name = result[0]

        cursor.execute("SELECT date, type FROM appointments WHERE id = ?", (appointment_id,))
        result = cursor.fetchone()
        if not result:
            return "Appointment not found", 404
        appointment_date, appt_type = result

        conn.close()

    except Exception as e:
        return f"Database error: {e}", 500

    return render_template(
        'upload.html',
        full_name=full_name,
        appointment_date=appointment_date,
        appt_type=appt_type
    )


@app.route('/upload_profile_pic', methods=['GET', 'POST'])
def upload_profile_pic():
    client_id = request.args.get('cid')

    if not client_id:
        return jsonify({"status": "error", "message": "Missing client ID"}), 400

    if request.method == 'POST':
        files = request.files.getlist('photos')
        if not files:
            return jsonify({"status": "error", "message": "No files received."}), 400

        file = files[0]  # Only use the first image
        if not file:
            return jsonify({"status": "error", "message": "Invalid file."}), 400

        # Get client name
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT full_name FROM clients WHERE id = ?", (client_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"status": "error", "message": "Client not found."}), 404
            full_name = result[0]
            conn.close()
        except Exception as e:
            return jsonify({"status": "error", "message": f"DB error: {e}"}), 500

        # Create save path
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in full_name).replace(" ", "_")
        filename = f"{safe_name}_id_{client_id}.png"
        save_path = os.path.join(PROFILE_PIC_DIR, filename)

        try:
            # Save image
            file.save(save_path)

            # Fix orientation if needed
            try:
                image = Image.open(save_path)
                for orientation in ExifTags.TAGS:
                    if ExifTags.TAGS[orientation] == "Orientation":
                        break
                exif = image._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)
                    if orientation_value == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation_value == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation_value == 8:
                        image = image.rotate(90, expand=True)
                    image.save(save_path)
                    print(f"✅ Orientation fixed for: {save_path}")
            except Exception as e:
                print(f"⚠️ Could not fix EXIF orientation: {e}")

            # Update database
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("UPDATE clients SET profile_picture = ? WHERE id = ?", (save_path, client_id))
            conn.commit()
            conn.close()

            return render_template(
                "upload_success.html",
                uploaded=1,
                full_name=full_name,
                appointment_date="Profile Picture",
                appt_type="Upload"
            )
        except Exception as e:
            return jsonify({"status": "error", "message": f"Save error: {e}"}), 500

    # For GET request, show upload form
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT full_name FROM clients WHERE id = ?", (client_id,))
        result = cursor.fetchone()
        conn.close()
        if not result:
            return "Client not found", 404
        full_name = result[0]
    except Exception as e:
        return f"DB error: {e}", 500

    return render_template(
        "upload.html",
        full_name=full_name,
        appointment_date="Profile Picture",
        appt_type="Upload"
    )


def start_flask_server():
    global DB_PATH, UPLOAD_BASE_DIR, PROFILE_PIC_DIR
    
    fallback_config_path = os.path.expanduser("~/SkinProData/config.json")

    while True:
        try:
            DB_PATH, UPLOAD_BASE_DIR, PROFILE_PIC_DIR = load_data_paths()
            break
        except Exception as e:
            print(f"❌ Failed to load data paths: {e}")

            expected_path = None
            if os.path.exists(fallback_config_path):
                try:
                    with open(fallback_config_path, "r") as f:
                        expected_path = json.load(f).get("data_dir")
                except:
                    pass

            root = Tk()
            root.withdraw()
            messagebox.showerror(
                "Missing Data Folder",
                f"The 'SkinProData' folder is missing.\n\n"
                f"Expected at: {expected_path if expected_path else '(unknown path)'}\n\n"
                "Please move it back to the original location."
            )
            root.destroy()

    log_path = os.path.join(os.path.dirname(DB_PATH), "flask_server_logs.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    try:
        logging.info("🚀 Starting Flask server on port 8000...")
        app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
    except SystemExit as e:
        logging.warning(f"⚠️ Flask shutdown with code {e}")
    except Exception as e:
        logging.error(f"🔥 Flask server crashed unexpectedly: {e}")
