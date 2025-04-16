# Add Credentials
Once you open the cloned repository in your preferred environemnt, add a file key.py in the repository. Note that this is gitignored while pushing to the remote branch. Add the following keys to the key.py file:

```bash
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
HANA_USER = ""
HANA_PW = ""
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_KEY = ""
AWS_DEFAULT_REGION = ""
HANA_INSTANCE = ""
```

# Creating a Virtual Environment
Creating a virtual environment for Python projects in Visual Studio (including Visual Studio Code) is an essential practice for managing dependencies and ensuring project isolation. Here’s a step-by-step guide:

Prerequisites

Python installed and added to your system PATH.

Visual Studio or Visual Studio Code installed, with the Python extension enabled.

Steps to Set Up a Python Virtual Environment
1. Open Visual Studio or Visual Studio Code

Launch the IDE from your Start menu or desktop shortcut.

2. Open or Create Your Project Folder

You can create a new folder for your project and open it in Visual Studio/VS Code.

In VS Code: Use File > Open Folder... and select your project directory.

3. Open the Integrated Terminal

In Visual Studio: Go to View > Terminal or press `Ctrl + `` to open the terminal pane.

In VS Code: Go to Terminal > New Terminal from the top menu.

4. Create the Virtual Environment

In the terminal, run the following command (replace env with your preferred environment name):

```bash
python -m venv env
```
This creates a folder named env (or your chosen name) containing the isolated Python environment.

5. Activate the Virtual Environment

On Windows, run:

```bash
.\env\Scripts\activate
```
On macOS/Linux, run:

```bash
source env/bin/activate
```
Once activated, your terminal prompt will be prefixed with the environment name (e.g., (env)).

6. Select the Python Interpreter (VS Code Only)

Press Ctrl+Shift+P, type Python: Select Interpreter, and choose the interpreter from your newly created virtual environment (it will be listed with your environment name).

# Install the Requirments
To install all the necessary dependencies, run the following command

```bash
pip install -r requirements.txt
```

# Change the namespaces

On line 151 in myapp/code.py, add the namespaces you used for structured and unstructured data, so only those are used in retrieval.

![image](https://github.com/user-attachments/assets/00980fbd-612f-4a93-8f89-10d3fd251ceb)

# Run The Django App

In the terminal, run the command:

```bash
python manage.py runserver
```
Open the URL that appears on the terminal in a browser, which will open the chatbot.
![image](https://github.com/user-attachments/assets/91e0325d-3de6-4d2c-b0b4-bb96052d65d0)

# Chat With The Chatbot
Select whether you want to ask a question based on structured or unstructured data and chat with the chatbot!. Kindly note that this version of the chatbot does not persist your question, which means you cannot follow up on something you previously asked.

