from flask import Flask, request, render_template_string
from google import genai
from google.genai import types
import os 

# --- Flask Configuration ---
# The app is configured with a secret key for security (though not strictly needed for this simple example)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_for_simple_adder_app'

# --- HTML Template (Using Jinja2 for dynamic content) ---
# Updated to use wide layout and large textarea fields
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grant Application Helper</title>
    <!-- Tailwind CSS CDN for modern, responsive styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f7f7f9;
        }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <!-- Changed max-w-md to w-full max-w-4xl for a wider, more screen-utilizing layout -->
    <div class="bg-white p-8 md:p-12 shadow-2xl rounded-xl w-full max-w-4xl">
        <h1 class="text-3xl font-bold text-gray-800 mb-6 text-center">
            Answer Helper
        </h1>

        <form method="POST" action="/" class="space-y-6">
            <div>
                <label for="text1" class="block text-sm font-medium text-gray-700 mb-1">
                    Grant Question:
                </label>
                <!-- Changed to textarea, applied min-h-[33vh] for 1/3 viewport height, and enabled vertical resize -->
                <textarea id="text1" name="text1" required
                       class="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out min-h-[25vh] resize-y">{% if text1 %}{{ text1 }}{% endif %}</textarea>
            </div>

            <div>
                <label for="text2" class="block text-sm font-medium text-gray-700 mb-1">
                    Answer specifications:
                </label>
                <!-- Changed to textarea, applied min-h-[33vh] for 1/3 viewport height, and enabled vertical resize -->
                <textarea id="text2" name="text2" required
                       class="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out min-h-[20vh] resize-y">{{ text2 }}</textarea>
            </div>

            <button type="submit"
                    class="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-md text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-150 ease-in-out transform hover:scale-[1.01]">
                Help me answer!
            </button>
        </form>

        {% if result %}
        <div class="mt-8 p-4 bg-green-50 border border-green-200 rounded-lg text-center shadow-inner">
            <p class="text-lg font-medium text-green-700">Answer:</p>
            <!-- Display result as a monospace string for clarity -->
            <p class="text-xl md:text-2xl font-mono font-bold text-green-900 mt-1 break-all">{{ result }}</p>
        </div>
        {% elif error %}
        <div class="mt-8 p-4 bg-red-50 border border-red-200 rounded-lg text-center shadow-inner">
            <p class="text-lg font-medium text-red-700">Error:</p>
            <p class="text-base text-red-900 mt-1">{{ error }}</p>
        </div>
        {% endif %}

    </div>
</body>
</html>
"""

def concatenate_strings(text1, text2):
    """
    Python function to perform string concatenation.
    """
    # Python's '+' operator naturally concatenates strings
    return text1 + text2

def generate_answer(text1, text2):
    client = genai.Client(
      vertexai=True,
      api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
  )

    si_text1 = text2

    model = "gemini-2.5-flash"
    contents = [
    types.Content(
        role="user",
        parts=[
        #types.Part.from_text(text="""Who is eligible for your services?""")
        types.Part.from_text(text=text1)
        ]
    ),
    ]
    tools = [
    types.Tool(
        retrieval=types.Retrieval(
        vertex_rag_store=types.VertexRagStore(
            rag_resources=[
            types.VertexRagStoreRagResource(
                rag_corpus=os.environ.get("GOOGLE_CLOUD_CORPUS_ADDRESS"),
            )
            ],
        )
        )
    )
    ]

    print("Running q ", text1)
    generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
    ),types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
    ),types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
    ),types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
    )],
    tools = tools,
    system_instruction=[types.Part.from_text(text=si_text1)],
    thinking_config=types.ThinkingConfig(
        thinking_budget=-1,
    ),
    )

    full_response = ""

    for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
            continue
    
        # Append the text from the current chunk to the full_response variable
        full_response += chunk.text
        #print(chunk.text, end="")

    return full_response

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route handler.
    Handles GET requests (displays the empty form) and
    POST requests (processes the form data and performs concatenation).
    """
    # Initialize variables for template
    result = None
    error = None
    text1_val = None
    
    # --- CHANGE: Set a default value for the second field ---
    DEFAULT_TEXT = "please respond in less than 300 words, with no formatting as if the response is to be entered in to a form field. Please respond from the perspective of Project Homelessness Connect and use formal language."
    text2_val = DEFAULT_TEXT

    if request.method == 'POST':
        # 1. Extract the text fields from the request
        text1_str = request.form.get('text1', '') 
        text2_str = request.form.get('text2', '')

        # Store values submitted by the user to keep them in the fields after submission
        text1_val = text1_str
        text2_val = text2_str # This overwrites the default with the user's submitted value

        try:
            # 2. Call the Python function directly with the string inputs
            #concatenated_result = concatenate_strings(text1_str, text2_str)
            concatenated_result = generate_answer(text1_str, text2_str)

            # 3. Set the result
            result = concatenated_result

        except Exception as e:
            # Catch any unexpected errors
            error = f"An unexpected error occurred: {e}"

    # 4. Render the template with the current state (initial form or result)
    return render_template_string(
        HTML_TEMPLATE,
        text1=text1_val,
        text2=text2_val,
        result=result,
        error=error
    )

if __name__ == '__main__':
    # When running directly, start the Flask development server
    print("Starting Flask app. Open your browser to http://127.0.0.1:5000/")
    # Setting debug=True is helpful during development
    app.run(debug=True)
