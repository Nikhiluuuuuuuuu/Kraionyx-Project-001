import json
import random
import uuid
import datetime

# Generate synthetic clinical data (patients, encounters, practitioners)
# Edge cases: missing fields, unicode characters, very long text, past/future dates.

def generate_patient():
    return {
        "id": str(uuid.uuid4()),
        "name": random.choice(["John Doe", "Jane Smith", "O'Connor, Tim", "Name With Ûñîçøđê"]),
        "dob": (datetime.date.today() - datetime.timedelta(days=random.randint(365, 36500))).isoformat(),
        "gender": random.choice(["male", "female", "other", "unknown", ""]),
        "edge_case_notes": random.choice(["Normal", "A" * 1000, ""])
    }

def generate_encounter(patient_id):
    return {
        "id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "practitioner_id": str(uuid.uuid4()),
        "status": random.choice(["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled"]),
        "type": random.choice(["outpatient", "emergency", "inpatient"]),
        "period": {
            "start": (datetime.datetime.now() - datetime.timedelta(minutes=random.randint(10, 100))).isoformat()
        }
    }

def generate_dataset(num_patients=100):
    data = {"patients": [], "encounters": []}
    for _ in range(num_patients):
        p = generate_patient()
        data["patients"].append(p)
        for _ in range(random.randint(1, 3)):
            e = generate_encounter(p["id"])
            data["encounters"].append(e)
    return data

if __name__ == "__main__":
    dataset = generate_dataset(500)
    with open("synthetic_clinical_data.json", "w") as f:
        json.dump(dataset, f, indent=2)
    print("Generated synthetic_clinical_data.json with 500 patients and their encounters.")
