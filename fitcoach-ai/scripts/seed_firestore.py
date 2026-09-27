#!/usr/bin/env python3
"""Seed script for initializing the Firestore 'exercises' collection for FitCoach AI."""

from google.cloud import firestore

# IMPORTANT: Hardcoded Project ID string as required for Agent Platform deployment
GCP_PROJECT_ID = "qwiklabs-gcp-03-1aaca47776f8"

SEED_EXERCISES = [
    {
        "id": "barbell_bench_press",
        "name": "Barbell Bench Press",
        "category": "Chest",
        "muscle_group": "Pectorals, Triceps, Anterior Deltoids",
        "difficulty": "Intermediate",
        "equipment": "Barbell, Flat Bench",
        "instructions": "Lie on flat bench, grip barbell slightly wider than shoulder-width, lower bar under control to mid-chest, press upwards until arms are extended."
    },
    {
        "id": "barbell_back_squat",
        "name": "Barbell Back Squat",
        "category": "Legs",
        "muscle_group": "Quadriceps, Glutes, Hamstrings",
        "difficulty": "Intermediate",
        "equipment": "Barbell, Squat Rack",
        "instructions": "Place barbell across upper back/traps, unrack, hinge hips back and bend knees to descend below parallel, drive through heels to return to standing."
    },
    {
        "id": "conventional_deadlift",
        "name": "Conventional Deadlift",
        "category": "Back",
        "muscle_group": "Erector Spinae, Hamstrings, Glutes, Latissimus Dorsi",
        "difficulty": "Advanced",
        "equipment": "Barbell, Weight Plates",
        "instructions": "Stand with feet hip-width under bar, hinge down to grip bar, keep chest up and flat back, drive legs into floor to pull bar up along shins to full lockout."
    },
    {
        "id": "bodyweight_pushups",
        "name": "Standard Push-Ups",
        "category": "Chest",
        "muscle_group": "Pectorals, Triceps, Core",
        "difficulty": "Beginner",
        "equipment": "Bodyweight",
        "instructions": "Place hands slightly wider than shoulder-width on floor, maintain straight plank line from head to heels, lower chest to floor and press back up."
    },
    {
        "id": "over_hand_pullups",
        "name": "Overhand Pull-Ups",
        "category": "Back",
        "muscle_group": "Latissimus Dorsi, Biceps, Upper Back",
        "difficulty": "Intermediate",
        "equipment": "Pull-Up Bar",
        "instructions": "Grip pull-up bar with palms facing away, pull chest up towards the bar by driving elbows down, lower back down under control."
    },
    {
        "id": "forearm_plank",
        "name": "Forearm Plank",
        "category": "Core",
        "muscle_group": "Rectus Abdominis, Transverse Abdominis",
        "difficulty": "Beginner",
        "equipment": "Bodyweight / Mat",
        "instructions": "Support body weight on forearms and toes, contract core to keep hips level with shoulders, hold position for target duration."
    }
]


def seed_database():
    print(f"Connecting to Firestore for project: {GCP_PROJECT_ID}...")
    db = firestore.Client(project=GCP_PROJECT_ID)
    collection_ref = db.collection("exercises")

    for exercise in SEED_EXERCISES:
        doc_id = exercise["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(exercise)
        print(f"  [+] Seeded exercise '{exercise['name']}' (ID: {doc_id})")

    print(f"\nSuccessfully seeded {len(SEED_EXERCISES)} exercises into Firestore!")


if __name__ == "__main__":
    seed_database()
