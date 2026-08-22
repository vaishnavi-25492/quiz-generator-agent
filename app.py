````python
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

# --------------------------------------------------
# Gemini Client
# --------------------------------------------------

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# --------------------------------------------------
# Generate Quiz
# --------------------------------------------------

def generate_quiz(topic, difficulty, number_of_questions):

    prompt = f"""
You are an AI Quiz Generator.

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
9. Do not use Markdown.
10. Do not put the JSON inside ```json code fences.

Use exactly this JSON structure:

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

    # --------------------------------------------------
    # Gemini API call
    # --------------------------------------------------

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    # Get Gemini's response text
    result = response.text.strip()

    # --------------------------------------------------
    # Clean possible Markdown code fences
    # --------------------------------------------------

    if result.startswith("```"):
        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

    # --------------------------------------------------
    # Convert response to Python dictionary
    # --------------------------------------------------

    try:
        quiz = json.loads(result)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Gemini returned invalid JSON: {error}"
        )

    # --------------------------------------------------
    # Validate quiz structure
    # --------------------------------------------------

    if "questions" not in quiz:
        raise ValueError(
            "Gemini response does not contain 'questions'."
        )

    questions = quiz["questions"]

    if not isinstance(questions, list):
        raise ValueError(
            "'questions' must be a list."
        )

    if len(questions) != number_of_questions:
        raise ValueError(
            f"Expected {number_of_questions} questions, "
            f"but Gemini returned {len(questions)}."
        )

    # Validate every question
    for index, question in enumerate(questions):

        if "question" not in question:
            raise ValueError(
                f"Question {index + 1} is missing 'question'."
            )

        if "options" not in question:
            raise ValueError(
                f"Question {index + 1} is missing 'options'."
            )

        if "answer" not in question:
            raise ValueError(
                f"Question {index + 1} is missing 'answer'."
            )

        if "explanation" not in question:
            raise ValueError(
                f"Question {index + 1} is missing 'explanation'."
            )

        if len(question["options"]) != 4:
            raise ValueError(
                f"Question {index + 1} must have exactly 4 options."
            )

        if question["answer"] not in [0, 1, 2, 3]:
            raise ValueError(
                f"Question {index + 1} has an invalid answer index."
            )

    return quiz


# --------------------------------------------------
# Home Page
# --------------------------------------------------

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# --------------------------------------------------
# Generate Quiz Route
# --------------------------------------------------

@app.route("/generate", methods=["POST"])
def generate():

    topic = request.form.get(
        "topic",
        ""
    ).strip()

    difficulty = request.form.get(
        "difficulty",
        "Medium"
    )

    try:
        number_of_questions = int(
            request.form.get(
                "num_questions",
                5
            )
        )
    except (TypeError, ValueError):

        number_of_questions = 5

    # --------------------------------------------------
    # Check topic
    # --------------------------------------------------

    if not topic:

        return render_template(
            "index.html",
            error="Please enter a topic."
        )

    # --------------------------------------------------
    # Limit number of questions
    # --------------------------------------------------

    if number_of_questions < 1:

        number_of_questions = 1

    if number_of_questions > 20:

        number_of_questions = 20

    # --------------------------------------------------
    # Generate quiz
    # --------------------------------------------------

    try:

        quiz = generate_quiz(
            topic,
            difficulty,
            number_of_questions
        )

        # Store quiz in session
        session["quiz"] = quiz
        session["topic"] = topic

        # Display quiz
        return render_template(
            "quiz.html",
            quiz=quiz,
            topic=topic,
            difficulty=difficulty
        )

    except Exception as error:

        print(
            f"Quiz generation error: {error}"
        )

        return render_template(
            "index.html",
            error=f"Quiz generation failed: {error}"
        )


# --------------------------------------------------
# Submit Quiz
# --------------------------------------------------

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

    # --------------------------------------------------
    # Check every question
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Calculate total
    # --------------------------------------------------

    total = len(
        quiz["questions"]
    )

    # --------------------------------------------------
    # Calculate percentage
    # --------------------------------------------------

    if total > 0:

        percentage = round(
            (score / total) * 100
        )

    else:

        percentage = 0

    # --------------------------------------------------
    # Performance message
    # --------------------------------------------------

    if percentage >= 80:

        performance = "Excellent!"

    elif percentage >= 60:

        performance = "Good Job!"

    elif percentage >= 40:

        performance = "Needs Improvement"

    else:

        performance = "Keep Practicing!"

    # --------------------------------------------------
    # Show result page
    # --------------------------------------------------

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


# --------------------------------------------------
# Run Application
# --------------------------------------------------

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
    )
````
