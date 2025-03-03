"""
Audio Query Processor - Utility Functions

This module contains utility functions for the Audio Query Processor application,
including audio recording and processing, API interactions, and database queries.

Author: Prateek Chhikara
"""

import whisper
import wave
import sounddevice as sd
import numpy as np
import requests
import threading
import pandas as pd
import queue
import json
import time
import weave
import os
from dotenv import load_dotenv
from jinja2 import Template
from prompts import COLUMN_SELECTION_PROMPT, QUERY_PROMPT
from config import MODEL_NAME, DATASET_DB

# Load environment variables
load_dotenv()

# Constants
SAMPLE_RATE = 16000
# DURATION = 10  # Record audio for 5 seconds (removed fixed duration)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

PIPECAT_URL = "http://localhost:8000/transcribe"  # PipeCat STT API endpoint

from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

# Global variables for recording
audio_queue = queue.Queue()
recording_thread = None
is_recording = False

def render_prompt(query, columns_with_description, fetched_columns, prompt_template):
    """
    Render a prompt template with the provided variables.
    
    Args:
        query (str): The user's query text
        columns_with_description (str): Description of available database columns
        fetched_columns (str): Columns that have been selected for the query
        prompt_template (str): The Jinja2 template to render
        
    Returns:
        str: The rendered prompt text
    """
    template = Template(prompt_template)
    return template.render(
        query=query, 
        columns_with_description=columns_with_description, 
        columns=fetched_columns
    )

@weave.op()
def audio2text(audio_file):
    """
    Transcribe an audio file to text using the Whisper model.
    
    Args:
        audio_file (str): Path to the audio file to transcribe
        
    Returns:
        str: The transcribed text
    """
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return result["text"]

def audio_callback(indata, frames, time, status):
    """
    Callback function for audio recording.
    
    This function is called for each audio block during recording
    and adds the audio data to the queue.
    
    Args:
        indata (numpy.ndarray): The recorded audio data
        frames (int): Number of frames
        time (CData): Time information
        status (CallbackFlags): Status flags
    """
    if is_recording:
        audio_queue.put(indata.copy())

def start_recording(sample_rate=SAMPLE_RATE):
    """
    Start recording audio from the microphone.
    
    Args:
        sample_rate (int): The sample rate for audio recording
        
    Returns:
        sd.InputStream: The audio stream object
    """
    global is_recording, recording_thread, audio_queue
    
    # Clear the queue
    while not audio_queue.empty():
        audio_queue.get()
    
    is_recording = True
    print("🎙️ Recording... Speak now!")
    
    # Start the stream
    stream = sd.InputStream(
        callback=audio_callback, 
        channels=1, 
        samplerate=sample_rate, 
        dtype=np.int16
    )
    stream.start()
    
    return stream

def stop_recording(stream, filename="audio.wav", sample_rate=SAMPLE_RATE):
    """
    Stop recording and save the audio to a file.
    
    Args:
        stream (sd.InputStream): The audio stream to stop
        filename (str): Path to save the recorded audio
        sample_rate (int): The sample rate of the audio
        
    Returns:
        str: Path to the saved audio file, or None if no audio was recorded
    """
    global is_recording, audio_queue
    
    is_recording = False
    stream.stop()
    stream.close()
    
    # Get all audio data from the queue
    audio_data = []
    while not audio_queue.empty():
        audio_data.append(audio_queue.get())
    
    if not audio_data:
        print("No audio data recorded!")
        return None
    
    # Combine all audio chunks
    audio = np.concatenate(audio_data)
    
    # Save to WAV file
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    
    print("✅ Recording complete!")
    return filename

def record_audio(filename="audio.wav", duration=None, sample_rate=SAMPLE_RATE):
    """
    Records audio from the microphone for a fixed duration.
    
    Note: This function is kept for backward compatibility.
    For dynamic recording, use start_recording() and stop_recording() instead.
    
    Args:
        filename (str): Path to save the recorded audio
        duration (int, optional): Duration in seconds to record
        sample_rate (int): The sample rate of the audio
        
    Returns:
        str: Path to the saved audio file, or None if duration is not provided
    """
    if duration is not None:
        print(f"🎙️ Recording for {duration} seconds...")
        audio = sd.rec(
            int(sample_rate * duration), 
            samplerate=sample_rate, 
            channels=1, 
            dtype=np.int16
        )
        sd.wait()
        
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
        
        print("✅ Recording complete!")
        return filename
    else:
        # For dynamic recording, this function should not be used directly
        print("For dynamic recording, use start_recording() and stop_recording() instead")
        return None

@weave.op()
def get_fields_description():
    """
    Get the description of database fields from the columns.json file.
    
    Returns:
        str: A formatted string containing column names and their descriptions
    """
    with open("columns.json", "r") as f:
        columns_with_description = json.load(f)

    columns_with_description_str = ""

    for column, description in columns_with_description.items():
        columns_with_description_str += f"Column: {column}\nDescription: {description}\n\n"

    return columns_with_description_str

@weave.op()
def generate_response(query, columns_with_description_str, required_columns, prompt):
    """
    Generate a response using the OpenAI API.
    
    Args:
        query (str): The user's query text
        columns_with_description_str (str): Description of available database columns
        required_columns (str): Columns that have been selected for the query
        prompt (str): The prompt template to use
        
    Returns:
        dict: The parsed JSON response from the API
    """
    # Render the prompt with the provided variables
    rendered_prompt = render_prompt(
        query, 
        columns_with_description_str, 
        required_columns, 
        prompt
    )

    # Call the OpenAI API
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": rendered_prompt}],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    # Return the parsed JSON response
    return json.loads(response.choices[0].message.content)

def call_weave(query, sort_by=None):
    """
    Execute a query against the Weave database.
    
    Args:
        query (dict): The query to execute
        sort_by (dict, optional): Sorting parameters for the query
        
    Returns:
        tuple: (pandas.DataFrame, int) - The query results and status code
    """
    try:
        # Initialize the Weave client
        client_db = weave.init(DATASET_DB)
        
        # Execute the query
        calls = client_db.get_calls(
            filter={"op_names": ["weave:///c-metrics/hallucination/op/Evaluation.evaluate:*"], 
                    "trace_roots_only": False},
            sort_by=sort_by,
            query=query,
            limit=10000,
            offset=0,
        )
        
        # Convert the results to a pandas DataFrame
        return calls.to_pandas(), 200
    except Exception as e:
        # Log the error (in a production environment, you would want to log this properly)
        print(f"Error executing Weave query: {str(e)}")
        return pd.DataFrame(), 500