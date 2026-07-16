from backend.command_manager import FirstLayerDMM
from backend.realtime_search_engine import RealtimeSearchEngine
from backend.automation import process_automation
from backend.speech_to_text import listen, SetAssistantStatus
from backend.chat_bot import ChatBot
from backend.text_to_speech import speak
from dotenv import dotenv_values
from time import sleep
import sys
import subprocess
import os

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search", "reminder", "weather", "news"]

def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    if not query_words:
        return ""
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]
    
    # Check if the query is a question and add a question mark if necessary.
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        # Add a period if the query is not a question.
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()


# Global state to track state transition print
last_print_was_listening = False

# Main Execution
def MainExecution():
    global last_print_was_listening
    try:
        SetAssistantStatus("Listening...")
        try:
            # speak("initializing jarvis. i am listening sir...")
            TaskExecution = False
            ImageExecution = False
            ImageGenerationQuery = ""
            
            if not last_print_was_listening:
                print("Listening...")
                last_print_was_listening = True
            Query = listen()
            if not Query:
                return False
            last_print_was_listening = False
            print(f"{Username} : {Query}")
                
            print("Thinking...")
            SetAssistantStatus("Thinking...")
            
            Decision = FirstLayerDMM(Query)
            print(f"Decision : {Decision}")
            
            G = any([i for i in Decision if i.startswith("general")])
            R = any([i for i in Decision if i.startswith("realtime")])
            
            Merged_query = " and ".join(
                [" ".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
            )
            
            for queries in Decision:
                if "generate " in queries:
                      ImageGenerationQuery = str(queries)
                      ImageExecution = True
                      
            for queries in Decision:
                if any(queries.startswith(func) for func in Functions):
                    response = process_automation(queries)
                    if response:
                        print(f"{Assistantname} : {response}")
                        speak(response)
                    TaskExecution = True
                        
            if ImageExecution == True:
                with open(r"Frontend\Files\ImageGeneration.data", "w", encoding='utf-8') as file:
                    file.write(f"{ImageGenerationQuery},True")
                    
                try:
                    p1 = subprocess.Popen([sys.executable, r'backend\image_generation.py'],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          stdin=subprocess.PIPE, shell=False)
                    subprocesses.append(p1)
                    
                except Exception as e:
                    print(f"Error starting image_generation.py: {e}")
                    
            if G and R or R:
                print("Searching...")
                SetAssistantStatus("Thinking...")
                Answer = RealtimeSearchEngine(QueryModifier(Merged_query))
                print(f"{Assistantname} : {Answer}")
                speak(Answer)
                return True
            
            else:
                for Queries in Decision:
                    if "general" in Queries:
                        QueryFinal = Queries.replace("general ","")
                        SetAssistantStatus("Thinking...")
                        Answer = ChatBot(QueryModifier(QueryFinal))
                        print(f"{Assistantname} : {Answer}")
                        speak(Answer)
                        return True
                    
                    elif "realtime" in Queries:
                        print("Searching...")
                        SetAssistantStatus("Thinking...")
                        QueryFinal = Queries.replace("realtime ","")
                        Answer = RealtimeSearchEngine(QueryModifier(QueryFinal))
                        print(f"{Assistantname} : {Answer}")
                        speak(Answer)
                        return True
                    
                    elif "exit" in Queries:
                        QueryFinal = "Okay, Bye!"
                        SetAssistantStatus("Thinking...")
                        Answer = ChatBot(QueryModifier(QueryFinal))
                        print(f"{Assistantname} : {Answer}")
                        speak(Answer)
                        os._exit(1)
        finally:
            SetAssistantStatus("Active")
    except Exception as e:
        err_msg = str(e).lower()
        if "getaddrinfo" in err_msg or "connection" in err_msg or "resolve" in err_msg or "offline" in err_msg:
            print(f"Network connection error in MainExecution: {e}. Retrying in 5 seconds...")
            sleep(5)
        else:
            print(f"Error in MainExecution: {e}. Retrying in 2 seconds...")
            sleep(2)
        return False
            
if __name__ == "__main__":
    while True:
        MainExecution()