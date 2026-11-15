"""Hospital Management REST API (System Under Test)
Modules: patient registration, appointments, medical records.
Run:  pip install flask  &&  python app.py   (listens on http://localhost:5000)
"""
import re
from datetime import date, datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
patients, appointments, records = {}, {}, {}
_ids = {"patient": 0, "appointment": 0, "record": 0}


def _next(kind):
    _ids[kind] += 1
    return _ids[kind]


def _err(code, msg):
    return jsonify({"error": msg}), code


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@app.post("/reset")
def reset():
    patients.clear(); appointments.clear(); records.clear()
    for k in _ids:
        _ids[k] = 0
    return jsonify({"status": "reset"}), 200


# ---------------- Patient registration ----------------
@app.post("/patients")
def create_patient():
    d = _body()
    if d is None:
        return _err(400, "Invalid or missing JSON body")
    name, age, phone, email = d.get("name"), d.get("age"), d.get("phone"), d.get("email")
    if not isinstance(name, str) or not name.strip():
        return _err(400, "name is required")
    if isinstance(age, bool) or not isinstance(age, int):
        return _err(400, "age must be an integer")
    if age < 0 or age > 120:
        return _err(400, "age must be between 0 and 120")
    if not isinstance(phone, str) or not re.fullmatch(r"\d{10}", phone):
        return _err(400, "phone must be exactly 10 digits")
    if not isinstance(email, str) or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return _err(400, "valid email is required")
    if any(p["email"].lower() == email.lower() for p in patients.values()):
        return _err(409, "email already registered")
    pid = _next("patient")
    patients[pid] = {"id": pid, "name": name.strip(), "age": age, "phone": phone, "email": email}
    return jsonify(patients[pid]), 201


@app.get("/patients/<int:pid>")
def get_patient(pid):
    if pid not in patients:
        return _err(404, "patient not found")
    return jsonify(patients[pid]), 200


# ---------------- Appointments ----------------
@app.post("/appointments")
def create_appointment():
    d = _body()
    if d is None:
        return _err(400, "Invalid or missing JSON body")
    pid, doctor, day, slot = d.get("patientId"), d.get("doctor"), d.get("date"), d.get("time")
    if isinstance(pid, bool) or not isinstance(pid, int):
        return _err(400, "patientId must be an integer")
    if not isinstance(doctor, str) or not doctor.strip():
        return _err(400, "doctor is required")
    if not isinstance(slot, str) or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", slot):
        return _err(400, "time must be HH:MM")
    try:
        when = datetime.strptime(day, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return _err(400, "date must be YYYY-MM-DD")
    if when < date.today():
        return _err(400, "date cannot be in the past")
    if pid not in patients:
        return _err(404, "patient not found")
    if any(a["doctor"] == doctor and a["date"] == day and a["time"] == slot for a in appointments.values()):
        return _err(409, "doctor slot already booked")
    aid = _next("appointment")
    appointments[aid] = {"id": aid, "patientId": pid, "doctor": doctor, "date": day, "time": slot}
    return jsonify(appointments[aid]), 201


@app.get("/appointments/<int:aid>")
def get_appointment(aid):
    if aid not in appointments:
        return _err(404, "appointment not found")
    return jsonify(appointments[aid]), 200


@app.delete("/appointments/<int:aid>")
def delete_appointment(aid):
    if aid not in appointments:
        return _err(404, "appointment not found")
    del appointments[aid]
    return jsonify({"status": "deleted"}), 200


# ---------------- Medical records ----------------
@app.post("/records")
def create_record():
    d = _body()
    if d is None:
        return _err(400, "Invalid or missing JSON body")
    pid, diagnosis = d.get("patientId"), d.get("diagnosis")
    if isinstance(pid, bool) or not isinstance(pid, int):
        return _err(400, "patientId must be an integer")
    if not isinstance(diagnosis, str) or not diagnosis.strip():
        return _err(400, "diagnosis is required")
    if pid not in patients:
        return _err(404, "patient not found")
    rid = _next("record")
    records[rid] = {"id": rid, "patientId": pid, "diagnosis": diagnosis.strip(),
                    "notes": d.get("notes", ""), "createdOn": date.today().isoformat()}
    return jsonify(records[rid]), 201


@app.get("/records/<int:pid>")
def get_records(pid):
    if pid not in patients:
        return _err(404, "patient not found")
    return jsonify([r for r in records.values() if r["patientId"] == pid]), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
