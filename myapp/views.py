from django.shortcuts import render
from .code import *  # Import the function from code.py
from django.http import JsonResponse

#=================UNSTRUCTURED DATA===================# 
def generate(question,anthropic,conn):
    
    sparql = write_query({"question": question},anthropic)
    response = execute_sparql(sparql,conn)
    answer = summarize_info(question, response,anthropic) # This response will be sent to the frontend
    return answer['final_answer']


def question_view(request):
    answer = ""
    document_link = None
    question = ""

    # Setup the database
    anthropic, conn = setup()

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if question:
            document_link = request.POST.get("link", "").strip()

            if document_link:
                print(document_link)
                store_data(document_link, anthropic, conn)

            answer = generate(question, anthropic, conn)
            print("answer: " + answer)

        response_data = {
            'answer': answer,
            'question': question,
            'document_link': document_link
        }

        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)

        # Optionally handle rendering for non-AJAX requests
        return render(request, 'home.html', response_data)

    # Handle GET requests or other non-POST requests
    return render(request, 'home.html')
 
 #========================STRUCTURED DATA=============================#

def question_view_structured(request):
    answer = ""
    document_link = None
    question = ""

    # Setup the database
    openAI, anthropic, conn = setup_structured()

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if question:
            document_link = request.POST.get("link", "").strip()

            if document_link:
                print(document_link)
                store_data(document_link, anthropic, conn)

            answer = process_question(question, conn, anthropic)
            print("answer: " + answer)

        response_data = {
            'answer': answer,
            'question': question,
            'document_link': document_link
        }

        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)

        # Optionally handle rendering for non-AJAX requests
        return render(request, 'home.html', response_data)

    # Handle GET requests or other non-POST requests
    return render(request, 'home.html')
