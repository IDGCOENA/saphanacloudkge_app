# Add Credentials
Once you open the cloned repository in your preferred environemnt, add a file key.py in the repository. Note that this is gitignored while pushing to the remote branch. Add the following keys to the key.py file:

_OPEN_AI_KEY = ""<br>
AWS_ACCESS_KEY_ID = ""<br>
AWS_SECRET_ACCESS_KEY = ""<br>
HANA_USER = ""<br>
HANA_PW = ""<br>
AZURE_OPENAI_ENDPOINT = ""<br>
AZURE_OPENAI_API_KEY = "" <br>
AWS_DEFAULT_REGION = ""<br>
HANA_ADMIN = ""<br>
HANA_ADMIN_PW = ""<br>__

# Install Requirements

We recommend creating a virtual environment. You can find how to do so [here](https://docs.python.org/3/library/venv.html). After creating the virtual environment, install run the command 
```bash
pip install -r requirements.txt
```
# Run The Django App

In the terminal, run the command:

```bash
python manage.py runserver
```
Open the URL that appears on the terminal in a browser, which will open the chatbot.
![image](https://github.com/user-attachments/assets/91e0325d-3de6-4d2c-b0b4-bb96052d65d0)

# Chat With The Chatbot
Select whether you want to ask a question based on structured or unstructured data and chat with the chatbot!. Kindly note that this version of the chatbot does not persist your question, which means you cannot follow up on something you previously asked.

