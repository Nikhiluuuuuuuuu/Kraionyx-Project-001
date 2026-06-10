import asyncio
import random
import time
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [PILOT-SIM] - %(levelname)s - %(message)s')

class HospitalPilotSimulator:
    def __init__(self, hospital_name: str, num_doctors: int, session_duration_minutes: int):
        self.hospital_name = hospital_name
        self.num_doctors = num_doctors
        self.session_duration_minutes = session_duration_minutes
        self.is_running = False

    async def simulate_doctor_session(self, doctor_id: str):
        logging.info(f"Doctor {doctor_id} started session.")
        session_end = time.time() + (self.session_duration_minutes * 60)
        
        while time.time() < session_end and self.is_running:
            # Simulate waiting for patient
            await asyncio.sleep(random.uniform(2, 5))
            
            patient_id = f"PAT-{uuid.uuid4().hex[:6].upper()}"
            logging.info(f"Doctor {doctor_id} starting consultation with patient {patient_id}")
            
            # Simulate streaming audio (which would go to Kraionyx STT)
            audio_duration = random.uniform(30, 180) # 30s to 3min consult
            logging.info(f"Doctor {doctor_id} streaming {audio_duration:.1f}s of audio to platform...")
            await asyncio.sleep(audio_duration / 10) # Time accelerated 10x for simulation
            
            logging.info(f"Consultation finished. Platform processing SOAP note for {patient_id}...")
            # Simulate latency
            await asyncio.sleep(random.uniform(1.5, 3.0))
            logging.info(f"SOAP note generated successfully for {patient_id}.")
            
        logging.info(f"Doctor {doctor_id} ended session.")

    async def run_pilot(self):
        logging.info(f"Starting simulated hospital pilot at {self.hospital_name} with {self.num_doctors} doctors.")
        self.is_running = True
        
        doctor_tasks = []
        for i in range(self.num_doctors):
            doctor_id = f"DOC-{i+1:03d}"
            doctor_tasks.append(asyncio.create_task(self.simulate_doctor_session(doctor_id)))
            
        await asyncio.gather(*doctor_tasks)
        logging.info("Hospital pilot simulation complete. Traffic data generated.")

if __name__ == "__main__":
    simulator = HospitalPilotSimulator("Apollo Hospital Pilot", num_doctors=5, session_duration_minutes=2)
    asyncio.run(simulator.run_pilot())
