"""
Audio Query Processor - Main Application

This module contains the main Streamlit application for the Audio Query Processor.
It provides a user interface for recording audio queries, processing them into
database queries, and displaying the results.

Author: Prateek Chhikara
"""

import streamlit as st
import time
import json
import weave
import os
from dotenv import load_dotenv
from utils import audio2text, start_recording, stop_recording, generate_response, get_fields_description, call_weave
from prompts import COLUMN_SELECTION_PROMPT, QUERY_PROMPT, SORT_BY_PROMPT
from config import PROJECT_NAME
# Load environment variables
load_dotenv()

def main():
    """
    Main function that runs the Streamlit application.
    
    This function initializes the Weave client, sets up the Streamlit page,
    handles user interactions for audio recording, processes the audio into text,
    generates database queries, and displays the results.
    """
    # Initialize weave with project name
    weave.init(PROJECT_NAME)

    # Set page configuration and styling
    st.set_page_config(
        page_title="Audio Query Processor",
        page_icon="🎙️",
        layout="wide"
    )
    
    # Apply custom CSS for better UI
    apply_custom_css()
    
    # Display application header
    display_header()
    
    # Initialize session state variables
    initialize_session_state()
    
    # Create recording controls
    display_recording_controls()
    
    # Display recording status with progress bar
    if st.session_state.recording:
        display_recording_progress()
    
    # Process the audio file if it exists
    if st.session_state.audio_file and not st.session_state.query_result:
        process_audio_file()
    
    # Display results if available
    if st.session_state.query_result:
        display_results()

def apply_custom_css():
    """Apply custom CSS styling to the Streamlit application."""
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

def display_header():
    """Display the application header and description."""
    st.title("🎙️ Audio Query Processor")
    st.markdown("##### Transform your voice into database queries seamlessly")

def initialize_session_state():
    """Initialize all required session state variables if they don't exist."""
    session_vars = {
        'recording': False,
        'audio_file': None,
        'query_result': None,
        'required_columns': None,
        'final_query': None,
        'stream': None,
        'weave_response': None,
        'status_code': None,
        'sort_by_query': None
    }
    
    for var, default in session_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default

def display_recording_controls():
    """Display the recording control buttons."""
    with st.container():
        st.markdown("### Recording Controls")
        col1, col2 = st.columns(2)
        
        # Start recording button
        with col1:
            if st.button("🎤 Start Recording", disabled=st.session_state.recording, type="primary"):
                st.session_state.recording = True
                st.session_state.audio_file = None
                st.session_state.query_result = None
                st.session_state.required_columns = None
                st.session_state.final_query = None
                st.session_state.stream = start_recording()
                st.experimental_rerun()
        
        # Stop recording button
        with col2:
            if st.button("⏹️ Stop Recording", disabled=not st.session_state.recording, type="secondary"):
                st.session_state.recording = False
                if st.session_state.stream:
                    st.session_state.audio_file = stop_recording(st.session_state.stream)
                    st.session_state.stream = None
                st.experimental_rerun()

def display_recording_progress():
    """Display a progress bar during recording."""
    st.markdown("---")
    st.info("🎙️ Recording in progress... Press 'Stop Recording' when finished.")
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress_bar.progress(i + 1)

def process_audio_file():
    """
    Process the recorded audio file.
    
    This function transcribes the audio, generates required columns,
    creates a database query, and fetches results from Weave.
    """
    with st.spinner("🔄 Processing your audio..."):
        # Transcribe the audio
        st.session_state.query_result = audio2text(st.session_state.audio_file)
        
        # Get column descriptions
        columns_with_description_str = get_fields_description()
        
        # Generate required columns
        st.session_state.required_columns = generate_response(
            st.session_state.query_result, 
            columns_with_description_str, 
            "", 
            COLUMN_SELECTION_PROMPT
        )['columns']

        # Filter columns to only include those in the allowed list
        with open("columns.json", "r") as f:
            columns_with_description = json.load(f)
        
        allowed_columns = list(columns_with_description.keys())
        st.session_state.required_columns = [
            column for column in st.session_state.required_columns 
            if column in allowed_columns
        ]

        # Generate final query
        st.session_state.final_query = generate_response(
            st.session_state.query_result, 
            columns_with_description_str, 
            st.session_state.required_columns, 
            QUERY_PROMPT
        )['query']

        # Generate sort by query
        st.session_state.sort_by_query = generate_response(
            st.session_state.query_result, 
            columns_with_description_str, 
            st.session_state.required_columns, 
            SORT_BY_PROMPT
        )['sort_by']
        
        # Call weave endpoint to execute the query
        st.session_state.weave_response, st.session_state.status_code = call_weave(
            st.session_state.final_query, 
            st.session_state.sort_by_query
        )

def display_results():
    """Display the query results and processing information."""
    st.markdown("---")
    
    # Create columns for results display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 📝 Transcribed Text")
        st.info(st.session_state.query_result)
    
    with col2:
        st.markdown("### 📊 Required Columns")
        st.code(json.dumps(st.session_state.required_columns, indent=2), language='json')
    
    with col3:
        st.markdown("### 🔍 Generated Query")
        st.code(json.dumps(st.session_state.final_query, indent=2), language='json')
    
    with col4:
        st.markdown("### 🔍 Sort By Query")
        st.code(json.dumps(st.session_state.sort_by_query, indent=2), language='json')

    # Display weave response which is a dataframe
    st.markdown("### 📊 Weave Response")
    if st.session_state.status_code == 200:
        # Display number of rows fetched from total rows
        st.markdown(f"🔍 **Found {len(st.session_state.weave_response):,} matching results** out of 195 total rows")
        st.dataframe(st.session_state.weave_response)
    else:
        st.error("Error fetching data from Weave")
    
    # Add a button to start over
    st.markdown("---")
    if st.button("🔄 Start Over", type="primary"):
        reset_session_state()
        st.experimental_rerun()

def reset_session_state():
    """Reset all session state variables to their default values."""
    session_vars = {
        'recording': False,
        'audio_file': None,
        'query_result': None,
        'required_columns': None,
        'final_query': None,
        'stream': None,
        'weave_response': None,
        'status_code': None,
        'sort_by_query': None
    }
    
    for var, default in session_vars.items():
        st.session_state[var] = default

if __name__ == "__main__":
    main()