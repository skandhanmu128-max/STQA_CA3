"""Python cross-check of the same 14-case matrix used in HospitalAPI.jmx.
Use it to confirm the API behaves as expected before/alongside the JMeter run.
Usage: python run_checks.py [base_url]"""
import csv, sys, time, uuid
from datetime import date, timedelta
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
FUTURE = (date.today() + timedelta(days=30)).isoformat()
results = []

def check(tcid, scenario, method, path, expected, body=None, raw=None):
    t0 = time.perf_counter()
    r = requests.request(method, BASE + path, json=body, data=raw,
                         headers={"Content-Type": "application/json"} if raw else None, timeout=5)
    ms = (time.perf_counter() - t0) * 1000
    ok = r.status_code == int(expected)
    results.append((tcid, scenario, expected, r.status_code, "PASS" if ok else "FAIL", round(ms, 1)))
    return r

requests.post(BASE + "/reset")
for row in csv.DictReader(open("patients.csv")):
    body = {"name": row["name"], "age": int(row["age"]), "phone": row["phone"], "email": row["email"]}
    check(row["tcid"], row["scenario"], "POST", "/patients", row["expected"], body)

pid = check("SETUP", "Register flow patient", "POST", "/patients", 201,
            {"name": "Flow Patient", "age": 40, "phone": "9123456780", "email": f"flow_{uuid.uuid4().hex}@x.com"}).json()["id"]
appt = {"patientId": pid, "doctor": "Dr. Rao", "date": FUTURE, "time": "10:30"}
aid = check("TC09", "Book valid appointment", "POST", "/appointments", 201, appt).json().get("id")
check("TC10", "Appointment unknown patient", "POST", "/appointments", 404, {**appt, "patientId": 9999, "time": "11:00"})
check("TC11", "Past-date appointment", "POST", "/appointments", 400, {**appt, "date": "2020-01-01", "time": "11:00"})
check("TC12", "Double-book same slot", "POST", "/appointments", 409, appt)
check("TC13", "Add medical record", "POST", "/records", 201, {"patientId": pid, "diagnosis": "Hypertension"})
check("TC14", "Records unknown patient", "GET", "/records/9999", 404)
check("EXTRA", "Fetch records for patient", "GET", f"/records/{pid}", 200)
check("EXTRA", "Delete appointment", "DELETE", f"/appointments/{aid}", 200)
check("EXTRA", "Malformed JSON body", "POST", "/patients", 400, raw="{bad json")

print(f"{'ID':<7}{'Scenario':<30}{'Exp':<6}{'Got':<6}{'Result':<7}{'ms':>7}")
for r in results:
    print(f"{r[0]:<7}{r[1]:<30}{r[2]!s:<6}{r[3]!s:<6}{r[4]:<7}{r[5]:>7}")
p = sum(r[4] == "PASS" for r in results); times = sorted(r[5] for r in results)
print(f"\nTotal {len(results)} | Passed {p} | Failed {len(results)-p} | "
      f"Avg {sum(times)/len(times):.1f} ms | Max {times[-1]} ms | Pass rate {100*p/len(results):.1f}%")
with open("../results/python_check_results.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "scenario", "expected", "actual", "result", "ms"]); w.writerows(results)
sys.exit(0 if p == len(results) else 1)
