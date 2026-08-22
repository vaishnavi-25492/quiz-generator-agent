from flask import Flask, render_template, request, session, redirect, url_for
from google import genai
import os
import json

app = Flask(__name__)

# Secret key for Flask sessions
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "quiz-generator-secret-key"
)

# OpenAI client
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)


def generate_quiz(topic, difficulty, number_of_questions):

    prompt = f"""
You are an AI Quiz Generator Agent.

Generate a multiple-choice quiz with the following requirements:

Topic: {topic}
Difficulty: {difficulty}
Number of Questions: {number_of_questions}

Rules:
1. Generate exactly {number_of_questions} questions.
2. Each question must have exactly 4 options.
3. Only one option must be correct.
4. Questions must be related to the given topic.
5. Match the requested difficulty.
6. Do not repeat questions.
7. Give a short explanation for every correct answer.
8. Return ONLY valid JSON.

Use this exact format:

{{
    "questions": [
        {{
            "question": "Question text",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "answer": 0,
            "explanation": "Explanation of the correct answer"
        }}
    ]
}}

For the answer value:
0 = Option A
1 = Option B
2 = Option C
3 = Option D
"""

    response = client.responses.create(
        model="gpt-5.6",
        input=prompt
    )

    result = response.output_text.strip()

    # Remove code fences if the AI returns JSON inside them
    if result.startswith("```"):
        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

    quiz = json.loads(result)

    return quiz


@app.route("/")
def home():

    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():

    topic = request.form.get("topic", "").strip()

    difficulty = request.form.get(
        "difficulty",
        "Medium"
    )

    number_of_questions = int(
        request.form.get(
            "num_questions",
            5
        )
    )

    # Check topic
    if not topic:

        return render_template(
            "index.html",
            error="Please enter a topic."
        )

    # Limit questions
    if number_of_questions < 1:
        number_of_questions = 1

    if number_of_questions > 20:
        number_of_questions = 20

    try:

        # Generate quiz using AI
        quiz = generate_quiz(
            topic,
            difficulty,
            number_of_questions
        )

        # Store quiz in session
        session["quiz"] = quiz
        session["topic"] = topic

        # Show quiz
        return render_template(
            "quiz.html",
            quiz=quiz,
            topic=topic,
            difficulty=difficulty
        )

    except Exception as error:

        return render_template(
            "index.html",
            error=f"Quiz generation failed: {error}"
        )


@app.route("/submit", methods=["POST"])
def submit():

    quiz = session.get("quiz")

    # If no quiz exists
    if not quiz:

        return redirect(
            url_for("home")
        )

    score = 0

    results = []

    # Check every question
    for index, question in enumerate(
        quiz["questions"]
    ):

        user_answer = request.form.get(
            f"question_{index}"
        )

        try:

            user_answer = int(
                user_answer
            )

        except (TypeError, ValueError):

            user_answer = -1

        correct_answer = question["answer"]

        # Check answer
        if user_answer == correct_answer:

            score += 1
            correct = True

        else:

            correct = False

        results.append({

            "question":
                question["question"],

            "options":
                question["options"],

            "user_answer":
                user_answer,

            "correct_answer":
                correct_answer,

            "explanation":
                question["explanation"],

            "correct":
                correct

        })

    # Total questions
    total = len(
        quiz["questions"]
    )

    # Calculate percentage
    if total > 0:

        percentage = round(
            (score / total) * 100
        )

    else:

        percentage = 0

    # Performance message
    if percentage >= 80:

        performance = "Excellent!"

    elif percentage >= 60:

        performance = "Good Job!"

    elif percentage >= 40:

        performance = "Needs Improvement"

    else:

        performance = "Keep Practicing!"

    # Show result page
    return render_template(
        "result.html",

        results=results,

        score=score,

        total=total,

        percentage=percentage,

        performance=performance,

        topic=session.get(
            "topic",
            "Quiz"
        )
    )


# Run application
if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )2
